import csv

#suppress warnings
import warnings
warnings.filterwarnings('ignore')

#import text tokenization library
import nltk
import polars as pl
from nltk.tokenize import word_tokenize

nltk.download('punkt')
nltk.download('tagsets')
nltk.download('averaged_perceptron_tagger_eng')


#import bbc-text.csv file into polars
df = pl.read_csv('bbc-text.csv')

print(df.head())

# for each transform the text column to a new tokens column
df = df.with_columns(pl.col('text').map_elements(word_tokenize).alias('tokens'))

print(df.head())  

df = df.explode('tokens')

#get tokens as numpy array
tokens = df['tokens'].to_numpy()

#tag the tokens with their part of speech
tagged_tokens = nltk.pos_tag(tokens)

#create new dataframe with the tagged token, the first element is the word and the second element is the tag
tagged_tokens = pl.DataFrame(tagged_tokens, schema=['word', 'tag'])

print(tagged_tokens.head())

#get the counts of each tag and create a seaborn plot of the counts showing from most to least common
import seaborn as sns
import matplotlib.pyplot as plt

tagged_tokens = tagged_tokens.group_by('tag').agg(pl.count('word').alias('count')).sort('count', descending=True)

sns.barplot(data=tagged_tokens.to_pandas(), x='tag', y='count')
plt.xticks(rotation=90)

plt.show()