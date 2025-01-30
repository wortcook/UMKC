#We are going to read the bbc-text.csv file and parse it into a list of dictionaries.

import csv

#import text tokenization library
import nltk
from nltk.tokenize import word_tokenize

nltk.download('punkt_tab')

def parse_csv(filename, delimiter=',', silence_errors=False):
    '''
    This function reads a CSV file with a given delimiter and returns a list of dictionaries.
    '''
    with open(filename,
              encoding='utf-8') as f:
            rows = csv.reader(f, delimiter=delimiter)
            
            #skip the header
            headers = next(rows)
            
            #initialize the list of dictionaries
            data = []
            
            #iterate over the rows
            
            for rowno, row in enumerate(rows, start=1):
                try:
                    record = dict(zip(headers, row))
                    data.append(record)
                except Exception as e:
                    if not silence_errors:
                        print(f"Row {rowno}: Couldn't parse {row}")
                        print(f"Row {rowno}: Reason {e}")
                        
    return data

def parse_bbc_text(filename):
    '''
    This function reads the bbc-text.csv file and returns a list of dictionaries.
    '''
    data = parse_csv(filename)
    
    for record in data:
        record['tokens'] = word_tokenize(record['text'])
        
    return data

def main():
    '''
    This is the main function.
    '''
    data = parse_bbc_text('bbc-text.csv')
    
    #now write out the tokens to a new file with the a new column indicating the tags for each token
    
    with open('bbc-text-tokens.csv', 'w', encoding='utf-8') as f:
        writer = csv.writer(f)
        
        #write the header
        writer.writerow(['category', 'text', 'tokens'])
        
        for record in data:
            writer.writerow([record['category'], record['text'], record['tokens']])
            
            
