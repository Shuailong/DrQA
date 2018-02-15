#!/usr/bin/env python3

'''
Analyze err file created by eval_err.py
created by Shuailong at 2018/2/10.

Load file. Count total error cases.
Input: case number (1-N)
Output: question, answer, candidates list (title, score)
Input: article title
Output: article full text
'''

import argparse
import prettytable
import logging
import json
import sys
import os
from shutil import copyfile
import pathlib

from termcolor import colored

from collections import Counter

from drqa import retriever


def print_case(d):
    question, answer, title, context, candidates = d['question'], d['answer'], d['title'], d['context'], d['candidates']
    print('\n===============================================\n')
    print(f'Question:\n{question}\n\nAnswer:\n{answer}\n')
    if title:
        print(f"Correct Title:\n{title}\n\nContext:\n")
        assert any(ans in context for ans in answer), f'{answer} not in {context}!'
        ans = [ans for ans in answer if ans in context][0]
        start = context.find(ans)
        end = start + len(ans)
        print(context[:start] + colored(context[start: end], 'green', attrs=['bold']) + context[end:])
    print('\nTop 5 docs:')
    table = prettytable.PrettyTable(
        ['Rank', 'Doc Id', 'Doc Score']
    )
    for i in range(len(candidates)):
        table.add_row([i + 1, candidates[i][0], '%.5g' % candidates[i][1]])
    print(table)


def correct_cases(remained_cases, corr_file):
    dirty = 0
    reformulated = 0

    for case_id, d in enumerate(remained_cases):
        print_case(d)
        tag = input('Need reformulate: ')
        if tag.lower() in ['1', 'y', 'yes']:
            q = input('Reformulated question:\n>> ')
            d['sq'] = q.strip()
            reformulated += 1
        d['dirty'] = 'Y'
        dirty += 1
        c = input('Continue (y/n): ')
        if c == 'n':
            break

    logger.info(f'Reformulated {reformulated} cases out of {dirty}. Remains {len(remained_cases) - dirty} cases to explore.')

    with open(corr_file, 'a') as f:
        for c in remained_cases:
            f.write(json.dumps(c) + '\n')
        f.flush()
    logger.info(f'Remaining {len(remained_cases)} cases saved back to {corr_file}.')


def main(args):
    corr_file = args.corr_file if args.corr_file is not None else os.path.splitext(args.error_file)[0] + '.corr'
    if not pathlib.Path(corr_file).is_file() or len(open(corr_file).readlines()) < 1:
        logger.info(f'Correction file does not exist or invalid. Created {corr_file} from {args.error_file}.')
        copyfile(args.error_file, corr_file)

    logger.info(f'Loading error cases from {corr_file}...')
    explored_cases = []
    remained_cases = []
    reformulated = 0
    with open(corr_file) as f:
        for line in f:
            case = json.loads(line)
            if 'dirty' in case:
                explored_cases.append(case)
            else:
                remained_cases.append(case)
            if 'sq' in case:
                reformulated += 1
    with open(corr_file, 'w') as f:
        for case in explored_cases:
            f.write(json.dumps(case) + '\n')
        f.flush()

    logger.info(f'Write back {len(explored_cases)} cases.')
    logger.info(f'{len(explored_cases) + len(remained_cases)} cases loaded.')
    logger.info(f'{len(explored_cases)} cases explored with {reformulated} reformulated.')
    logger.info(f'{len(remained_cases)} cases needs to be expored.')

    correct_cases(remained_cases, corr_file)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--error_file', type=str, default=None, help='error cases', required=True)
    parser.add_argument('--corr_file', type=str, default=None, help='corrected error cases.')
    parser.add_argument('--doc-db', type=str, default=None,
                        help='Path to Document DB')

    args = parser.parse_args()

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter('%(asctime)s: [ %(message)s ]', '%m/%d/%Y %I:%M:%S %p')
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)

    main(args)
