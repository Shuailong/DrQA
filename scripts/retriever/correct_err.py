#!/usr/bin/env python3

'''
Rewrite the inappropriate question.
created by Shuailong at 2018/2/10.
'''

import argparse
import prettytable
import logging
import json
import sys
import os
import pathlib
from termcolor import colored
from collections import Counter
import readline

from drqa import retriever


def rlinput(prompt, prefill=''):
    readline.set_startup_hook(lambda: readline.insert_text(prefill))
    try:
        return input(prompt)
    finally:
        readline.set_startup_hook()


def print_case(d):
    question, answer, title, context, candidates = d['question'], d['answer'], d['title'], d['context'], d['candidates']
    question = colored(question, color='yellow', attrs=['bold'])
    print(f'Question:\n{question}\n\nAnswer:\n{answer}\n')
    if title:
        print(f"Correct Title:\n{title}\n\nContext:\n")
        assert any(ans in context for ans in answer), f'{answer} not in {context}!'
        ans = [ans for ans in answer if ans in context][0]
        start = context.find(ans)
        end = start + len(ans)
        print(context[:start] + colored(context[start: end], color='green', attrs=['bold']) + context[end:])
    print('\nTop 5 docs:')
    table = prettytable.PrettyTable(
        ['Rank', 'Doc Id', 'Doc Score']
    )
    for i in range(len(candidates)):
        table.add_row([i + 1, candidates[i][0], '%.5g' % candidates[i][1]])
    print(table)


def correct_cases(cases, corr_file):
    out_f = open(corr_file, 'a')
    reformulated = 0
    passed = 0
    for case_id, d in enumerate(cases):
        print('\n######################')
        print(f'#### {case_id + 1:4} / {len(cases):4}  ####')
        print('######################')
        print_case(d)

        if d['title'].replace('_', ' ') in [c[0] for c in d['candidates']]:
            print('True title matches top 5 candidates! Skip.')
        else:
            tag = rlinput('Need reformulate (y/n): ', prefill='n')
            if tag.lower().strip() != 'n':
                q = rlinput('Reformulated question:\n>> ', prefill=d['question'])
                d['sq'] = q.strip()
                reformulated += 1

        passed += 1
        out_f.write(json.dumps(d) + '\n')
        out_f.flush()
        c = rlinput('Continue (y/n): ', prefill='y')
        if c.lower().strip() == 'n':
            break
    out_f.close()
    logger.info(f'Reformulated {reformulated} cases out of {passed} cases. Remains {len(cases) - passed} cases to explore.')


def main(args):
    corr_file = os.path.splitext(args.error_file)[0] + '.corr'

    logger.info(f'Loading error cases from {args.error_file}, start from {args.start_index}.')
    cases = []
    with open(args.error_file) as f:
        for i, line in enumerate(f):
            if i + 1 >= args.start_index:
                cases.append(json.loads(line))
    logger.info(f'{len(cases)} cases loaded.')
    correct_cases(cases, corr_file)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Adapt SQuAD questions for open domain QA')
    parser.add_argument('--error_file', type=str, default=None, help='error cases file to read from', required=True)
    parser.add_argument('--start_index', type=int, help='index number to start with (1 based). ', required=True)

    args = parser.parse_args()

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter('%(asctime)s: [ %(message)s ]', '%m/%d/%Y %I:%M:%S %p')
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)

    main(args)
