import warnings
warnings.filterwarnings('ignore')

#import text tokenization library
import nltk
import polars as pl
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer
from nltk.corpus import wordnet
from nltk.corpus import stopwords

#stopwords
nltk.download('stopwords')

nltk.download('wordnet')

wordnet.ensure_loaded()


def tokenize(df):
    '''
    This function tokenizes the text column in the dataframe.
    '''
    return df.with_columns(pl.col('stemmed').map_elements(word_tokenize).alias('tokens'))

def stem(df):
    '''
    This function stems the tokens in the dataframe.
    '''
    return df.with_columns(pl.col('tweet').map_elements(PorterStemmer().stem).alias('stemmed'))

def tag(df):
    '''
    This function tags the tokens in the dataframe.
    '''
    # df.with_columns(pl.col('tokens').map_elements(nltk.pos_tag).alias('tagged_tokens'))
    #for each row in tokens, create a new column with just the tags that are in the second element of the tuple
    return df.with_columns(pl.col('tokens').map_elements(lambda x: [y[1] for y in nltk.pos_tag(x)]).alias('token_tags'))

def map_to_wordnet(df):
    '''
    This function maps the tags to the wordnet tags.
    '''
    def map_tags(tags):
        ret_tags = []
        for tag in tags:
            if tag.startswith('N'):
                ret_tags.append(wordnet.NOUN)
            elif tag.startswith('V'):
                ret_tags.append(wordnet.VERB)
            elif tag.startswith('R'):
                ret_tags.append(wordnet.ADV)
            elif tag.startswith('J'):
                ret_tags.append(wordnet.ADJ)
            else:
                ret_tags.append(None)
        
        #return as series
        return pl.Series(ret_tags)
        
    return df.with_columns(pl.col('token_tags').map_elements(map_tags).alias('wordnet_tags'))

def lemmaization(df):
    '''
    This function lemmatizes the original tweet column.
    '''
    #create a lemmatizer
    lemmatizer = nltk.WordNetLemmatizer()
    
    #lemmatize the tweet column
    return df.with_columns(pl.col('tweet').map_elements(lemmatizer.lemmatize).alias('lemmas'))

def remove_stopwords(df):
    '''
    This function removes the stopwords from the original tweet column.
    '''
    #get the stopwords
    stop_words = set(stopwords.words('english'))
    
    #remove the stopwords from the tweet column
    return df.with_columns(pl.col('tweet').map_elements(lambda x: ' '.join([word for word in x.split() if word not in stop_words])).alias('no_stopwords'))


# create a polars pipeline to tokenize the text column
df = (pl.read_csv('twitter20220831.csv')
      .pipe(stem)
      .pipe(lemmaization)
      .pipe(remove_stopwords)
      .pipe(tokenize)
      .pipe(tag)
      .pipe(map_to_wordnet)
      )

print(df.head())