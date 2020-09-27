# -*- coding: utf-8 -*-
"""
MEighty Influence App

Scott Harrison - 2020-09-26

App that allows exploration of music group influences.


"""

# =============================================================================
# %% initialisation
# =============================================================================

# -----------------------------------------------------------------------------
# --- define parameters
# -----------------------------------------------------------------------------
logo_img = 'MEighty-logo.png'
search_url = 'https://en.wikipedia.org/wiki/'


# -----------------------------------------------------------------------------
# --- import libraries
# -----------------------------------------------------------------------------
import pandas as pd
import numpy as np
import pickle
import streamlit as st
from urllib.request import urlopen
from bs4 import BeautifulSoup
import lxml


# =============================================================================
# %% functions
# =============================================================================

# -----------------------------------------------------------------------------
# create_markdown_text 
# -----------------------------------------------------------------------------
@st.cache
def create_markdown_text(header_number, header_text):
    """
    Generates text for a markdown header in specified format

    Parameters
    ----------
    header_number : INTEGER
        Specifies the header level.
    header_text : STRING
        Header text.

    Returns
    -------
    markdown_text : STRING
        Markdown header text

    """

    # create string
    markdown_text = "<h{} style='text-align: center; color: grey;'>{}</h{}>".\
        format(str(header_number), header_text, str(header_number))
        
    return markdown_text


# -----------------------------------------------------------------------------
# initialiseLists 
# -----------------------------------------------------------------------------
#@st.cache
def initialiseLists(seedURL):
    dfEntitiesInit = pd.DataFrame({'Index': [0], 
                               'Distance' : [0], 
                               'URL' : [seedURL], 
                               'Name' : ['']})
    dfEntitiesInit['Index'] = dfEntitiesInit['Index'].astype(int)
    dfLinksInit = pd.DataFrame({'Band': [], 'Associated' : []})
    dfLinksInit['Band'] = dfLinksInit['Band'].astype(int)
    dfLinksInit['Associated'] = dfLinksInit['Associated'].astype(int)
    return(dfEntitiesInit, dfLinksInit)


# -----------------------------------------------------------------------------
# getEntity 
# -----------------------------------------------------------------------------
#@st.cache(suppress_st_warning=True)
def getEntity(dfEntities):
    # get first entity with no details
    entityRows = dfEntities[dfEntities['Name']=='']
    entityURL = entityRows.iloc[0]['URL']
    entityIndex = entityRows.iloc[0]['Index']
    return(entityURL, entityIndex)


# -----------------------------------------------------------------------------
# getEntity 
# -----------------------------------------------------------------------------
#@st.cache
def findAssociatedActs(actRef):
    # only run for valid URL
    if 'https://en.wikipedia.org/wiki/' in actRef:
        # open and read page
        page = urlopen(actRef)
        soup = BeautifulSoup(page, 'lxml')
        # get associated acts
        newBand = []
        newRef = []
        links = soup.find_all("tr")
        for link in links:
            if str(link).find('Associated acts') > -1:
                assoc = link.find_all("a")
                for a in assoc:
                    newBand.append(a.get("title"))
                    newRef.append('https://en.wikipedia.org'+a.get("href")) # NEEDS UPADTING - TEST WITH State_of_Alert, Gone_(band), Mother_Superior_(band)
                break
        # return results
        return(pd.DataFrame({'Act': soup.h1.find(text=True), 
                             'Associated Act': newBand, 
                             'Associated Link': newRef}))
    return(pd.DataFrame({'Act': [], 'Associated Act': [], 'Associated Link': []}))


# -----------------------------------------------------------------------------
# updateLists 
# -----------------------------------------------------------------------------
#@st.cache
def updateLists(dfEntities, dfLinks, newDetails, oldIndex):
    # update if new entities exist
    if len(newDetails) > 0:
        # update existing entity
        entName = newDetails.iloc[0]['Act']
        dfEntities.loc[dfEntities['Index']==oldIndex, 'Name'] = entName
        # update new entities - exclude existing and append
        newEnt = newDetails[~newDetails['Associated Link'].\
                                 isin(dfEntities['URL'])]
        newEntities = pd.DataFrame({
                'Index': [a+max(dfEntities['Index'])+1 for a in list(range(len(newEnt)))], 
                'Distance' : list(np.repeat(dfEntities.loc[dfEntities['Index']==oldIndex]['Distance']+1, 
                                       len(newEnt))),
                'URL' : list(newEnt['Associated Link']), 
                'Name' : list(np.repeat('', len(newEnt)))})
        dfEntities = dfEntities.append(newEntities, ignore_index=True)
        # update links 
        newIndex = dfEntities[dfEntities['URL'].\
                              isin(newDetails['Associated Link'])]['Index']
        newLink = pd.DataFrame({'Band': oldIndex, 'Associated' : newIndex})
        dfLinks = dfLinks.append(newLink, ignore_index=True)
    # ensure name is captured
    if len(dfEntities.loc[dfEntities['Index']==oldIndex, 'Name']) < 2:
        entName = dfEntities.loc[dfEntities['Index']==oldIndex]['URL']
        dfEntities.loc[dfEntities['Index']==oldIndex, 'Name'] = entName
    # return updated details
    return(dfEntities, dfLinks)

# -----------------------------------------------------------------------------
# pickle functions
# -----------------------------------------------------------------------------
def pickle_item(item, file):
    with open(file, 'wb') as pfile:
        pickle.dump(item, pfile)
def unpickle_item(file):
    with open(file, 'rb') as pfile:
        item = pickle.load(pfile)
    return(item)


# =============================================================================
# %% page set up
# =============================================================================

# -----------------------------------------------------------------------------
# --- header
# -----------------------------------------------------------------------------
# banner
st.image(logo_img, use_column_width=False)
# app title
st.markdown(create_markdown_text(1, "Influences"), unsafe_allow_html=True)
# app description
st.markdown("""> Allows a user to graphically investigate the influences of 
            music groups.""")
            
            
# =============================================================================
# %% select the group
# =============================================================================

# -----------------------------------------------------------------------------
# --- get name and search for options
# -----------------------------------------------------------------------------
# get band
input_band = st.text_input('Band to review:')
# clean name
input_band = input_band.replace(' ', '_')
# create url
current_url = search_url+input_band
# initialise process
try:
    dfEntities = unpickle_item(input_band+'_ent.pkl')
    dfLinks = unpickle_item(input_band+'_lnk.pkl')
except:
    dfEntities, dfLinks = initialiseLists(current_url)


# =============================================================================
# %% get influences
# =============================================================================

def extractNextLayer(dfEntities, dfLinks):
    # get next band
    oldBand, oldIndex = getEntity(dfEntities)
    # get associated acts
    newDetails = findAssociatedActs(oldBand)
    # update details
    dfEntities, dfLinks = updateLists(dfEntities, dfLinks, newDetails, oldIndex)
    return(dfEntities, dfLinks)
           
if st.button('Extract Layer'):
    progress_bar = st.progress(0)
    entities_in_layer = len(dfEntities[dfEntities['Name']==''])
    for i in range(entities_in_layer):
        progress_bar.progress((i+1)/entities_in_layer)
        dfEntities, dfLinks = extractNextLayer(dfEntities, dfLinks)


# =============================================================================
# %% output current state
# =============================================================================

st.dataframe(dfEntities)
pickle_item(dfEntities.copy(), input_band+'_ent.pkl')
pickle_item(dfLinks.copy(), input_band+'_lnk.pkl')