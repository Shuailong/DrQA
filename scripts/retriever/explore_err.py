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
import code
import sys

from termcolor import colored

from collections import Counter

from multiprocessing import Pool as ProcessPool
from multiprocessing.util import Finalize

from drqa import retriever


def usage():
    print(banner)


def c(case_id=None):
    if not isinstance(case_id, int):
        print('case_id should be INT type')
    elif case_id < 0 or case_id >= len(cases):
        print(f'case id should be in range [0, {len(cases) - 1}]')
    else:
        d = cases[case_id]
        question, answer, title, context, candidates = d['question'], d['answer'], d['title'], d['context'], d['candidates']
        print(f'Question:\n{question}\n\nAnswer:\n{answer}\n\nTop 5 docs:')
        table = prettytable.PrettyTable(
            ['Rank', 'Doc Id', 'Doc Score']
        )
        for i in range(len(candidates)):
            table.add_row([i + 1, candidates[i][0], '%.5g' % candidates[i][1]])
        print(table)
        if title:
            print(f"\nCorrect Title:\n{title}\n\nContext:\n")
            assert any(ans in context for ans in answer), f'{answer} not in {context}!'
            ans = [ans for ans in answer if ans in context][0]
            start = context.find(ans)
            end = start + len(ans)
            print(context[:start] + colored(context[start: end], 'green', attrs=['bold']) + context[end:])


def content(title=None):
    if not isinstance(title, str):
        print('title should be STR type')
    global PROCESS_DB
    text = PROCESS_DB.get_doc_text(title)
    print(f'Content for title `{title}`:\n{text}')


# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--error_file', type=str, default=None, required=True)
    parser.add_argument('--doc-db', type=str, default=None,
                        help='Path to Document DB')

    args = parser.parse_args()

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter('%(asctime)s: [ %(message)s ]', '%m/%d/%Y %I:%M:%S %p')
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)

    logger.info(f'Loading error cases from {args.error_file}')

    cases = []
    with open(args.error_file) as f:
        for line in f:
            case = json.loads(line)
            cases.append(case)

    logger.info(f'{len(cases)} error cases loaded.')

    PROCESS_DB = retriever.DocDB(db_path=args.doc_db)

    banner = """
Interactive Error Analyzer
>> usage()
>> c(case_id=1)
>> content(title='Richard Broxton Onians')
    """

    code.interact(banner=banner, local=locals())
