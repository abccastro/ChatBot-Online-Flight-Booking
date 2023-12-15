import re
import urllib3
import demoji
import utils

from flashtext import KeywordProcessor
from flashtext import KeywordProcessor
from bs4 import BeautifulSoup
from emot.emo_unicode import EMOTICONS_EMO
from nltk.tokenize import word_tokenize
import nltk
nltk.download('vader_lexicon')


def remove_email_address(text):
    pattern_email = r'\b[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,7}\b'
    return re.sub(pattern_email, '', text)


def remove_hyperlink(text):
    pattern_url = r'https?://(?:www\.)?[\w\.-]+(?:\.[a-z]{2,})+(?:/[-\w\.,/]*)*(?:\?[\w\%&=]*)?'
    return re.sub(pattern_url, '', text)


def remove_attherate(text):
    pattern_attherate = r'[@]'
    return re.sub(pattern_attherate, '', text)


def remove_hashtag(text):
    pattern_hashtag = r'#\w+'
    return re.sub(pattern_hashtag, '', text)


def replace_html_char(text):
    text = text.replace("&amp;", "and")
    text = text.replace("&lt;", "<")
    return text


def get_emojis():
    emoji_dict = KeywordProcessor()
    try:
        for k, v in EMOTICONS_EMO.items():
            words = re.split(r',| or ', v.lower())
            # get only the first element. remove "smiley" word.
            word = words[0].replace(" smiley", "")
            k = k.replace("‑", "-")
            # put in a dictionary
            emoji_dict.add_keyword(k, words[0])

        # additional emojis
        emoji_dict.add_keyword("<3", "heart")
        emoji_dict.add_keyword("</3", "heartbroken")
    except Exception as err:
        print(f"ERROR: {err}")

    return emoji_dict


def replace_emojis_unicode(text):
    demoji.download_codes()
    return demoji.replace_with_desc(text, sep=' ')


def replace_nonascii_characters(text):
    # List of all non-ascii characters that needs to be replaced
    text = re.sub('[İı]', 'I', '[â]', 'A', text)
    return text


def get_slang_words(webscraped=False):
    # TODO: Put in a config file
    filename = './dictionary/slang_words_dictionary.pkl'

    slang_word_dict = KeywordProcessor()
    try:
        if webscraped:
            # build slang words dictionary by webscraping
            slang_word_dict = webscrape_slang_words()
            # update the existing pickle file
            utils.save_pickle_file(slang_word_dict, filename)
        else:
            # open a pickle file
            slang_word_dict = utils.open_pickle_file(filename)
    except Exception as err:
        print(f"ERROR: {err}")
        print(f"Importing slang words dictionary from file..")
        # open a pickle file
        slang_word_dict = utils.open_pickle_file(filename)

    return slang_word_dict


def webscrape_slang_words():
    http = urllib3.PoolManager()
    slang_word_dict = KeywordProcessor()

    word_replacement_dict = {'ikr': 'i know right'}
    try:
        for i in range(97, 123):
            # site where the slang words will be scraped
            page = http.request(
                'GET', 'https://www.noslang.com/dictioary/'+chr(i))
            soup = BeautifulSoup(page.data, 'html.parser')

            for elem in soup.findAll('div', class_="dictonary-word"):
                slang_word = elem.find('abbr').get_text()

                key = slang_word[0: slang_word.rfind(":")-1]
                value = elem.find(
                    'dd', class_="dictonary-replacement").get_text()

                # put in a dictionary
                slang_word_dict.add_keyword(
                    key.lower(), word_replacement_dict.get(key.lower(), value.lower()))
    except Exception as err:
        print(f"ERROR: {err}")

    return slang_word_dict


def replace_whitespace(text):
    pattern = r'\s+'
    return re.sub(pattern, ' ', text)


def remove_stopwords(text, list_of_stopwords):
    # Tokenize the text
    tokens = word_tokenize(text)
    # Remove stop words from the tokenized text
    filtered_tokens = [
        token for token in tokens if token not in list_of_stopwords and "-" not in token and token.isalpha()]
    # Join the non-stopwords back into a string
    filtered_text = " ".join(filtered_tokens)

    return filtered_text
