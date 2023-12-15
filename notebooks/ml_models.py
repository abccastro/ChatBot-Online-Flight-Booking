"""
##########################################################################################################################

Machine Learning Models Methods

This Python file contains a set of utility methods aimed at providing reusable functions for tasks related to machine 
learning model in a program. 

Usage:
- Import this file in your Python script.
- Call the desired utility functions to perform specific tasks within your program.

Example Usage:
>>> import ml_models as md
>>> generate_roberta_labels = md.generate_roberta_labels(data)
>>> print(generate_roberta_labels)
Output: <data with sentiment labels>

########################################################################################################################
"""

import multiprocessing
import os
import nltk

from nltk.sentiment.vader import SentimentIntensityAnalyzer
from nltk.corpus import stopwords
from scipy.special import softmax


nltk.download('vader_lexicon')


def polarity_score_roberta(data, model, tokenizer, max_length=512): 
    '''
    A function that computes the polarity score using the RoBERTa pre-trained model
    '''

    # Tokenize and truncate/pad the input text
    # Note: Adjust this based on the model's maximum sequence length
    encoded_text = tokenizer(data, return_tensors='tf', max_length=max_length, truncation=True, padding=True)
    
    output = model(**encoded_text)
    scores = output[0][0].numpy()
    scores = softmax(scores)
    
    scores_dict = {
        "roberta_neg": scores[0],
        'roberta_neu': scores[1],
        'roberta_pos': scores[2]
    }
    
    return scores_dict


def generate_roberta_labels(text, model, tokenizer):
    '''
    A function for generating sentiment labels using RoBERTa on movie reviews
    '''
    # Get roberta scores
    scores = polarity_score_roberta(text, model, tokenizer)
    roberta_neg, roberta_neu, roberta_pos = scores['roberta_neg'], scores['roberta_neu'], scores['roberta_pos']

    sentiment_results_dict = {'positive': roberta_pos, 
                              'negative': roberta_neg, 
                              'neutral': roberta_neu}

    highest_sentiment = max(sentiment_results_dict.items(), key=lambda x: x[1])

    return highest_sentiment[0]


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