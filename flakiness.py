#!/usr/bin/python
import random
import logging
from collections import namedtuple, defaultdict


class FP(namedtuple('FP', 'failures, passes')):
  def flakiness(self):
    if self.failures + self.passes == 0:
      return float('nan')
    return float(self.failures) / (self.failures + self.passes)

  def add(self, test_runs):
    p = sum(test_runs)
    f = len(test_runs) - p
    logging.debug('adding %s => f %i p %i to F %i, P %i', test_runs, f, p, self.failures,
        self.passes)
    return FP(failures=self.failures + f, passes=self.passes + p)


class Stats(object):
  def __init__(self):
    self._tests = defaultdict(lambda: FP(0, 0))
    self._overall = FP(0, 0)

  def update_suite_run(self, run):
    dir_runs = defaultdict(lambda: True)
    for test, test_runs in run.iteritems():
      logging.debug('run test %s: %s', test, test_runs)
      self._tests[test] = self._tests[test].add(test_runs)
      for i, r in enumerate(test_runs):
        dir_runs[i] &= r
    dir_runs = [v for _, v in sorted(dir_runs.iteritems())]
    logging.debug('run_dir: %s', dir_runs)
    self._overall = self._overall.add(dir_runs)

  def flakiness_report(self):
    return 'dir: %5.1f%% tests %s' % (
        100 * self._overall.flakiness(),
        ', '.join(
          '%5s: %5.1f%%' % (test, 100 * self._tests[test].flakiness())
          for test in sorted(self._tests)
        )
    )

def run_with_tries(flakiness, tries):
  results = []
  while len(results) < tries:
    results.append(random.random() > flakiness)
    if results[-1]:
      break
  return results

def run_test_suite(flakinesses, tries):
  return {
      test_name: run_with_tries(flakiness, tries)
      for test_name, flakiness in flakinesses.iteritems()
  }


def main(opts):
  s = Stats()
  flakinesses = dict(opts.test_fprs)
  for i in xrange(opts.max_num):
    s.update_suite_run(run_test_suite(flakinesses, opts.tries))
    if (i+1) % opts.every == 0 or i +1 == opts.max_num:
      print '%10i: %s' % (i+1, s.flakiness_report())

if __name__ == '__main__':
  # Estimate directory flakiness.
  import argparse, sys

  def test_fp(a):
    name, perc = a.split(':')
    rate = float(perc) / 100
    return name, rate

  parser = argparse.ArgumentParser()
  parser.add_argument('-v', '--verbose', action='count')
  parser.add_argument('-n', '--max-num', dest='max_num', type=int, default=10**6)
  parser.add_argument('-e', '--every', type=int, default=1000)
  parser.add_argument('-t', '--tries', default=2, type=int)
  parser.add_argument('test_fprs', nargs='+', type=test_fp,
                      help='test:fpr as in A:10, as many as you want.')
  opts = parser.parse_args()

  logging.basicConfig(level=0 if opts.verbose else logging.WARN)

  sys.exit(main(opts) or 0)
