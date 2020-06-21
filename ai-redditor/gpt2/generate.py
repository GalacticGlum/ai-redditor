import re
import time
import torch
import argparse
from tqdm import tqdm
from pathlib import Path
from transformers import (
    set_seed,
    AutoTokenizer, 
    AutoModelWithLMHead
)

parser = argparse.ArgumentParser(description='Generate text from a model with an language modelling head.')
parser.add_argument('model_name_or_path', type=str, help='The model checkpoint for weights initialization (i.e. a pretrained model).')
parser.add_argument('--prompt', type=str, default=None, help='A prompt for the model. Leave to None for no prompt.')
parser.add_argument('--samples', type=int, default=1, help='The number of samples to generate. Defaults to 1.')
parser.add_argument('--top-k', type=int, default=300, help='The number of highest probability vocabulary tokens ' +
                    'to keep for top-k-filtering. Between 1 and infinity. Default to 300.')
parser.add_argument('--top-p', type=float, default=1, help='The cumulative probability of parameter highest probability ' +
                    'vocabulary tokens to keep for nucleus sampling. Must be between 0 and 1. Default to 1.')
parser.add_argument('--num-return-sequences', type=int, default=10, help='The number of sequences to return per iteration. ' + 
                    'Defaults to 10.')
parser.add_argument('--max-iterations', type=int, default=5, help='Maximum number of iterations. Defaults to 5.')
parser.add_argument('--max-length', type=int, default=250, help='Maximum number of tokens to generate in a single iteration.')
parser.add_argument('--seed', type=int, default=None, help='The seed of the random engine.')
parser.add_argument('--translate-token', type=str, default=None, help='The query/answer separator token (translation separator token). ' +
                    'If not specified, the first additional special token from the tokenizer is used.')
parser.add_argument('--profile', dest='show_profile', action='store_true', help='Show profiling results.')
args = parser.parse_args()

tokenizer = AutoTokenizer.from_pretrained(args.model_name_or_path)
model = AutoModelWithLMHead.from_pretrained(args.model_name_or_path)

print('- Loaded model and tokenizer from \'{}\''.format(args.model_name_or_path))

# Set seed to reproduce results.
if args.seed is None:
    # We use the current time as the seed rather than letting numpy seed
    # since we want to achieve consistent results across sessions.
    # Source: https://stackoverflow.com/a/45573061/7614083
    t = int(time.time() * 1000.0)
    args.seed = ((t & 0xff000000) >> 24) + ((t & 0x00ff0000) >> 8) + ((t & 0x0000ff00) <<  8) + ((t & 0x000000ff) << 24)

set_seed(args.seed)

print('- Set seed to {}'.format(args.seed))

# The tokenizer should only have a single additional special token,
# which is the translate token. If no overwrite is specified, we use this.
translate_token = args.translate_token or tokenizer.additional_special_tokens[0]
split_pattern = (
    f'^{re.escape(tokenizer.bos_token)}(?P<prompt>.+?)'
    f'(?:{re.escape(translate_token)}(?P<response>.+?))*'
    f'{re.escape(tokenizer.eos_token)}'
)

split_regex = re.compile(split_pattern, flags=re.MULTILINE | re.DOTALL)

if args.prompt is None:
    args.prompt = '{}[WP]'.format(tokenizer.bos_token)
 
prompt_ids = tokenizer.encode(args.prompt, return_tensors='pt').to(model.device)
print('- Encoded prompt into token ids')

class ProfileResult:
    '''
    A profile result for a single sample.

    '''

    def __init__(self, generate_durations=None, fail_count=0, iteration_count=0):
        '''
        Initializes a new :class:`ProfileResult` object.

        :param generate_durations:
            The time, in seconds, that it took to generate the sample
            for each iteration stored as a list.
        :param fail_count:
            The number of failed samples.
        :param iteration_count:
            The number of iterations that it took to generate the sample.
    
        '''

        self.generate_durations = generate_durations or list()
        self.fail_count = fail_count
        self.iteration_count = iteration_count

results = []
profiling_results = []

current_iteration = 0
with tqdm(total=args.samples) as progress_bar:
    profile_result = ProfileResult()
    while len(results) < args.samples and current_iteration < args.max_iterations:
        current_iteration += 1

        start_time = time.time()
        generated = model.generate(
            prompt_ids,
            bos_token_id=tokenizer.bos_token_id,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.pad_token_id,
            top_k=args.top_k, top_p=args.top_p,
            num_return_sequences=args.num_return_sequences,
            max_length=args.max_length + len(prompt_ids), do_sample=True
        )

        profile_result.generate_durations.append(time.time() - start_time)

        for i in range(generated.size()[0]):
            if len(results) >= args.samples: break

            sentence_tokens = generated[i, :].tolist()
            decoded = tokenizer.decode(sentence_tokens)

            match = split_regex.match(decoded)
            if not match:
                progress_bar.write('- Could not split generated sequence into parts. Skipping...')
                profile_result.fail_count += 1
                continue

            prompt = match.group('prompt').strip()
            response = match.group('response').strip()
            if prompt is None or response is None:
                progress_bar.write('- Generated sequence has no prompt or response. Skipping...')
                profile_result.fail_count += 1
                continue

            progress_bar.update(1)
            results.append((prompt, response))

            # Update profile results
            profile_result.iteration_count = current_iteration
            profiling_results.append(profile_result)

print(results)

if args.show_profile:
    print('##### Profile Results #####')
    for index, profile_result in enumerate(profiling_results):
        print('***** Sample {} *****'.format(index + 1))
        print('- Took {} iterations (failed {} times).'.format(
            profile_result.iteration_count, profile_result.fail_count
        ))

        print('- Generate Durations: {} seconds'.format(', '.join(
            str(round(duration, 2))for duration in profile_result.generate_durations)
        ))
        
        print('- Average Duration: {:.2f} seconds'.format(
            sum(profile_result.generate_durations) / len(profile_result.generate_durations)
        ))

    print('###########################')
