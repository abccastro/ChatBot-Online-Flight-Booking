import pandas as pd
import numpy as np
import re
import nltk
import text_preprocessing as tp
import utils
import spacy
import seaborn as sb
import demoji
import contractions

from nltk.corpus import stopwords
from nltk.corpus import words
from nltk.stem import WordNetLemmatizer
from flashtext import KeywordProcessor
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import nltk
nltk.download('vader_lexicon')

input_text = ""
slang_word_dict = {}
emoji_dict = {}


def generate_vader_labels(text):
    '''
    A function for generating sentiment labels using Vader on movie reviews
    '''
    sid = SentimentIntensityAnalyzer()
    sentiment_scores = sid.polarity_scores(text)

    # Determine the overall sentiment
    if sentiment_scores['compound'] >= 0.1:
        sentiment = 'positive'
    elif sentiment_scores['compound'] <= -0.1:
        sentiment = 'negative'
    else:
        sentiment = 'neutral'

    return sentiment


def conduct_text_preprocessing(text):

    try:
        # Remove non-grammatical text
        text = tp.remove_email_address(input_text)
        text = tp.remove_hyperlink(text)
        text = tp.replace_html_char(text)
        text = tp.remove_attherate(text)
        text = tp.remove_hashtag(text)

        # Replace emojis in the 'review' column
        text = tp.replace_emojis_unicode(text)
        text = emoji_dict.replace_keywords(text)

        # Handle contractions
        text = contractions.fix(text)

        # Replace slang words
        text = slang_word_dict.replace_keywords(text)

        # Remove leading and trailing whitespaces, and multiple whitespaces
        text = text.strip()
        text = tp.replace_whitespace(text)

    except Exception as err:
        print(f"ERROR: {err}")
        print(f"Input Text: {text}")

    return text


def start_sentiment(review):
    """
    Function to clean and generate sentiment for the review
    """
    slang_word_dict = tp.get_slang_words(webscraped=True)
    emoji_dict = tp.get_emojis()

    preprocessed_text = conduct_text_preprocessing(review)
    sentiment = generate_vader_labels(review)

    return sentiment