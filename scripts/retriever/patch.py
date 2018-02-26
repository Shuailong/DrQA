#!/usr/bin/env python3
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.
"""
Integrate the corrected case into the SQuAD-v1.1 dev dataset
"""

import argparse
import json

parser = argparse.ArgumentParser()
parser.add_argument('--dataset', type=str, required=True, help='SQuAD v1.1 dataset in txt format')
parser.add_argument('--correction', type=str, required=True, help='SQuAD v1.1 correction file in txt format')
parser.add_argument('--output', type=str, required=True, help='output file name')
args = parser.parse_args()

# Read dataset
cases = []
with open(args.dataset) as f:
    for line in f:
        cases.append(json.loads(line))
print(f'{len(cases)} total cases loaded.')

question_map = {}
with open(args.correction) as f:
    for line in f:
        case = json.loads(line)
        if 'sq' in case and case['sq']:
            question_map[case['question']] = case['sq']
print(f'{len(question_map)} question pairs loaded.')

# Iterate and write question-answer pairs
replaced = 0
with open(args.output, 'w') as f:
    for d in cases:
        question = d['question']
        answer = d['answer']
        if question in question_map:
            question = question_map[question]
            replaced += 1
        f.write(json.dumps({'question': question, 'answer': answer}))
        f.write('\n')
print(f'{replaced} questions replaced.')
