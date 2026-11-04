"""Require the saved-observation replay to match the published analysis exactly."""
import argparse,json
from pathlib import Path

def equal_results(expected, actual):
    # Execution time may differ; all results, input hashes and metadata must match.
    first={k:v for k,v in expected.items() if k!='analyzed_at'}
    second={k:v for k,v in actual.items() if k!='analyzed_at'}
    return first==second

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('expected',type=Path);parser.add_argument('actual',type=Path)
    args=parser.parse_args()
    expected=json.loads(args.expected.read_text(encoding='utf8'))
    actual=json.loads(args.actual.read_text(encoding='utf8'))
    if not equal_results(expected,actual):raise SystemExit('FAIL: replay differs beyond analyzed_at')
    print('PASS: exact analysis equality except analyzed_at; all observation and validation hashes match')

if __name__=='__main__':main()
