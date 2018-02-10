#!/usr/bin/env python3
# Copyright 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the license found in the
# LICENSE file in the root directory of this source tree.

"""Analyze the errors of the DrQA retriever module.

Modified by Shuailong at 2018/2/9.
For the questions which the retriever fails, save the question,
answer and top-n candidates returned by the retriever.

"""

import regex as re
import logging
import argparse
import json
import time
import os
from tqdm import tqdm

from multiprocessing import Pool as ProcessPool
from multiprocessing.util import Finalize
from multiprocessing import Manager
from functools import partial
from drqa import retriever, tokenizers
from drqa.retriever import utils

# ------------------------------------------------------------------------------
# Multiprocessing target functions.
# ------------------------------------------------------------------------------

PROCESS_TOK = None
PROCESS_DB = None


def init(tokenizer_class, tokenizer_opts, db_class, db_opts):
    global PROCESS_TOK, PROCESS_DB
    PROCESS_TOK = tokenizer_class(**tokenizer_opts)
    Finalize(PROCESS_TOK, PROCESS_TOK.shutdown, exitpriority=100)
    PROCESS_DB = db_class(**db_opts)
    Finalize(PROCESS_DB, PROCESS_DB.close, exitpriority=100)


def regex_match(text, pattern):
    """Test if a regex pattern is contained within a text."""
    try:
        pattern = re.compile(
            pattern,
            flags=re.IGNORECASE + re.UNICODE + re.MULTILINE,
        )
    except BaseException:
        return False
    return pattern.search(text) is not None


def has_answer(answer, doc_id, match):
    """Check if a document contains an answer string.

    If `match` is string, token matching is done between the text and answer.
    If `match` is regex, we search the whole text with the regex.
    """
    global PROCESS_DB, PROCESS_TOK
    text_raw = PROCESS_DB.get_doc_text(doc_id)
    text = utils.normalize(text_raw)
    if match == 'string':
        # Answer is a list of possible strings
        text = PROCESS_TOK.tokenize(text).words(uncased=True)
        for single_answer in answer:
            single_answer = utils.normalize(single_answer)
            single_answer = PROCESS_TOK.tokenize(single_answer)
            single_answer = single_answer.words(uncased=True)
            for i in range(0, len(text) - len(single_answer) + 1):
                if single_answer == text[i: i + len(single_answer)]:
                    return True
    elif match == 'regex':
        # Answer is a regex
        single_answer = utils.normalize(answer[0])
        if regex_match(text, single_answer):
            return True
    return False


def get_err(idx, answer_doc, q, match):
    """Search through all the top docs to see if they have the answer."""
    question, answer, (doc_ids, doc_scores) = answer_doc
    ans_candidates = []
    for i, doc_id in enumerate(doc_ids):
        success = has_answer(answer, doc_id, match)
        ans_candidates.append((doc_id, doc_scores[i]))
        if success:
            return idx, 0, q

    error_msg = {
        'question': question,
        'answer': answer,
        'candidates': ans_candidates
    }
    q.put(error_msg)
    return idx, 1, q


def res_writer(q, file):
    '''listens for messages on the q, writes to file.'''
    with open(file, 'w') as f:
        while True:
            m = q.get()
            if m == 'kill':
                break
            f.write(json.dumps(m) + '\n')
            f.flush()


def update(res):
    i, res, q = res
    global pbar
    global errors
    global remains
    errors[i] = res
    pbar.update()
    remains -= 1
    if remains == 0:
        q.put('kill')


# ------------------------------------------------------------------------------
# Main
# ------------------------------------------------------------------------------


if __name__ == '__main__':
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter('%(asctime)s: [ %(message)s ]',
                            '%m/%d/%Y %I:%M:%S %p')
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)

    parser = argparse.ArgumentParser()
    parser.add_argument('dataset', type=str, default=None)
    parser.add_argument('--model', type=str, default=None)
    parser.add_argument('--doc-db', type=str, default=None,
                        help='Path to Document DB')
    parser.add_argument('--tokenizer', type=str, default='regexp')
    parser.add_argument('--n-docs', type=int, default=5)
    parser.add_argument('--num-workers', type=int, default=None)
    parser.add_argument('--match', type=str, default='string',
                        choices=['regex', 'string'])
    parser.add_argument('--out-dir', type=str, default='/tmp',
                        help=('Directory to write error file to '
                              '(<dataset>-<model>.errs)'))
    args = parser.parse_args()

    # start time
    start = time.time()

    # read all the data and store it
    logger.info('Reading data ...')
    questions = []
    answers = []

    for line in open(args.dataset):
        data = json.loads(line)
        question = data['question']
        answer = data['answer']
        questions.append(question)
        answers.append(answer)

    # get the closest docs for each question.
    logger.info('Initializing ranker...')
    ranker = retriever.get_class('tfidf')(tfidf_path=args.model)

    logger.info('Ranking...')
    closest_docs = ranker.batch_closest_docs(
        questions, k=args.n_docs, num_workers=args.num_workers
    )
    answers_docs = list(zip(questions, answers, closest_docs))

    # define processes
    tok_class = tokenizers.get_class(args.tokenizer)
    tok_opts = {}
    db_class = retriever.DocDB
    db_opts = {'db_path': args.doc_db}
    processes = ProcessPool(
        processes=args.num_workers,
        initializer=init,
        initargs=(tok_class, tok_opts, db_class, db_opts)
    )

    # compute the scores for each pair, and print the statistics
    logger.info('Retrieving and computing scores...')

    q = Manager().Queue()
    model = os.path.splitext(os.path.basename(args.model or 'default'))[0]
    basename = os.path.splitext(os.path.basename(args.dataset))[0]
    outfile = os.path.join(args.out_dir, basename + '-' + model + '.errs')

    N = len(questions)
    global remains
    remains = N
    global pbar
    pbar = tqdm(total=N)
    global errors
    errors = [None] * N

    get_err_partial = partial(get_err, match=args.match)
    processes.apply_async(res_writer, (q, outfile))
    for i in range(N):
        processes.apply_async(get_err_partial, args=(i, answers_docs[i], q), callback=update)

    processes.close()
    processes.join()
    pbar.close()

    filename = os.path.basename(args.dataset)
    stats = (
        "\n" + "-" * 50 + "\n" +
        "{filename}\n" +
        "{outfile}\n" +
        "Examples:\t\t\t{total}\n" +
        "Mismatches in top {k}:\t\t{m}\n" +
        "Mismatch % in top {k}:\t\t{p:2.2f}\n" +
        "Total time:\t\t\t{t:2.4f} (s)\n"
    ).format(
        filename=filename,
        outfile=outfile,
        total=len(errors),
        k=args.n_docs,
        m=sum(errors),
        p=(sum(errors) / len(errors) * 100),
        t=time.time() - start,
    )

    print(stats)
