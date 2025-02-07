#suppress warnings
import warnings
warnings.filterwarnings('ignore')

#import text tokenization library
import nltk
import polars as pl
from nltk.tokenize import word_tokenize
from collections import Counter

nltk.download('punkt')
nltk.download('tagsets')
nltk.download('averaged_perceptron_tagger_eng')

def tokenize(df):
    '''
    This function tokenizes the text column in the dataframe.
    '''
    return df.with_columns(pl.col('text').map_elements(word_tokenize).alias('tokens'))

def tag(df):
    '''
    This function tags the tokens in the dataframe.
    '''
    # df.with_columns(pl.col('tokens').map_elements(nltk.pos_tag).alias('tagged_tokens'))
    #for each row in tokens, create a new column with just the tags that are in the second element of the tuple
    return df.with_columns(pl.col('tokens').map_elements(lambda x: [y[1] for y in nltk.pos_tag(x)]).alias('token_tags'))


def count_tags(df):
    '''
    This function counts the tags in the dataframe.
    '''    
    #for each row in the token_tags column get a count of the tags and return the counts as a dictionary of tags to total counts
    return Counter([tag for tags in df['token_tags'] for tag in tags])

#create a polars pipeline to tokenize the text column
df = (pl.read_csv('bbc-text.csv')
      .pipe(tokenize)
      .pipe(tag)
      )

tag_counts = count_tags(df)

#sort by the values
tag_counts = dict(sorted(tag_counts.items(), key=lambda x: x[1], reverse=True))

#print the tag counts as a formatted table
print(f"{'Tag':<10} {'Count':<10}")
for tag, count in tag_counts.items():
    print(f"{tag:<10} {count:<10}")

import seaborn as sns
import matplotlib.pyplot as plt

#plot the tag counts
sns.barplot(x=tag_counts.keys(), y=tag_counts.values())
#rotate the x-axis labels
plt.xticks(rotation=90)

plt.show()

