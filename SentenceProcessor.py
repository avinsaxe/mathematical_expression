import sys
import re
import nltk
nltk.download('wordnet')
#from nltk.corpus import stopwords
from nltk.corpus import wordnet as wn
nltk.download('averaged_perceptron_tagger')
from CosineSimilarity import CosineSimilarity

# the only stop words in our sentences
stopwords = ['the', 'a', 'an','of'] # caution, don't use "A" in the sentence. ex. Vehicle A < Vehicle B

# all these does not help in coverting from natural language to maths, so remove these
replacements = ['should', 'would', 'shall', 'will', 'must', 'might', 'to be', 'could', 'is', 'has', 'have', 'be',
                'should be', 'would be', 'shall be', 'will be', 'must be', 'might be', 'could be']

# first remove those having more length
# e.g. we should first check if "should be" exists or not and then check for "should"
# Nevertheless, this is not required as I have implemented it now. Don't remove to be on safe side
replacements = sorted(replacements, key=lambda x: -len(x))

# currently this is the only word which I could think of that we need to preserve. This will help in converting < or > to =
reserved_words = ['by', 'is']


class SentenceProcessor:

    def __init__(self,sentence,window_size):
        self.operands=[]
        self.sentence=sentence.lower()
        self.tags=dict()   #This will store the key as the word in the sentence and the appropriate tag as the value. less_than  is tagged as operator
        self.transformedSentence=None
        self.window=int(window_size)
        self.operandDictionaryFile= 'operandDictionary.txt'
        self.operatorDictionaryFile='operatorDictionary.txt'
        self.words=[]
        self.operandDictionary=[] 
        self.operatorDictionary=[] # not used anymore, not needed. Make the code which uses this inactive, but don't remove 
        self.operatorMapping=[] # this is a list of tuples e.g. ('plus', '+'), ('add', '+'), ('times', '*')
        self.operators = [] # list of operators that we support
        self.tokens = [] # this is the final list of tokens after processing
        self.phrases_k_size=[]
        self.tagged_operands=[]
        self.tagged_operators=[]
        self.phrases_1_size_operator=[]
        self.initializeDictionary()
        self.initializeSentence()
        self.initializePhrasesOfSizeK()
        self.initializePhrasesOfSize1Operator()
        self.cosineSim=CosineSimilarity()
        self.merger=[]

        # This is a list and will store the transformed sentence made entirely of keys from the tags and relative position as in
        # the original sentence

    def initializeSentence(self):

        #print replacements
        
        print "original:", self.sentence
        # remove articles/stop words
        for _ in stopwords:
            self.sentence = re.sub(" "+_+" ", ' ', self.sentence)
            if (self.sentence.split(' ',1)[0] == _):
                self.sentence = self.sentence.split(' ',1)[1]
        
        print "after removing articles:", self.sentence
        
        # remove "replacements"
        for _ in replacements:
            self.sentence = re.sub(" "+_+" ", ' ', self.sentence)
        self.sentence = re.sub('is is is', 'is', self.sentence)
        self.sentence = re.sub('is is', 'is', self.sentence)

        print "after removing replacements:", self.sentence

        # replace text with actual operators
        for _ in self.operatorMapping:
            self.sentence = re.sub(_[0], " " + _[1] + " ", self.sentence)
        print "after replacing text with operators:", self.sentence

        # change <number><unit> to <number> e.g. 10meters --> 10
        self.sentence = re.sub('(\d+)[^ \d]*', ' \g<1>', self.sentence)
        print "after changing numbers:", self.sentence

        if self.sentence!=None:
            self.words=self.sentence.split()   #a list of words
            print "after splitting the processed sentence:", self.words

        # This is for merging the parts of string 
        # e.g. we have all words in the sentence as a list at this moment.
        # after this step, we will have <part A> <operator> <part B>
        self.tokens = []
        n = len(self.words)
        i = 0
        token = ""
        while i<n:
            if self.words[i] in self.operators or self.words[i] in reserved_words:
                self.tokens.append(token.strip())
                token = ""
                self.tokens.append(self.words[i])
            else:
                token += " "+self.words[i]
            i += 1
        self.tokens.append(token)
        print "After merging the parts of sentence together:", self.tokens

        # now we need to process the each element of "self.tokens" list
        # for each element:
        #   if it is not an operator and not in reserved word:
        #        if it is "[]":
        #           split the next token on "and". we will get the lower and upper limit which might be numbers or variable names                
        #        else:
        #           use cosine similarity to get the actual variable name from the natural language description
        #           remember, we might not need the window of 3 approach anymore, don't remove it though
        #   else:
        #       keep operators and reserved words as is for future processing, we 
        #       will come back to these once we have the actual variables in the sentence 



    def initializeDictionary(self):
        with open(self.operandDictionaryFile, "r") as ins:
            array = []
            for line in ins.readlines():
                splits=line.split("\n")
                splits=splits[0:-1]   #removing the extra '' blank character getting added
                self.operandDictionary.append(splits)
                self.operands.append(splits[0])

        array = []
        with open(self.operatorDictionaryFile,"r") as ins:
            for line in ins.readlines():
                #print line
                splits=line.split(",")
                self.operators.append(splits[-1][0:-1].strip())
                for _ in splits[0:-1]:
                    array.append((_.strip(), splits[-1][0:-1]))
        #print array
        self.operatorMapping = sorted(array, key=lambda x:-len(x[0]))
        print self.operators
        #print array
        

    def initializePhrasesOfSizeK(self):
        for k in range(0,len(self.words)-self.window+1):  #possible starting points of the string
            phrase=self.words[k:k+int(self.window)]
            self.phrases_k_size.append(phrase)

    def initializePhrasesOfSize1Operator(self):
        for k in range(0,len(self.words)):  #possible starting points of the string
            phrase=self.words[k:k+1]
            self.phrases_1_size_operator.append(phrase)
        # print "?????",self.phrases_1_size_operator


    #processes a single sentence
    def processSentence(self):
        self.operandTagging()
        self.operatorTagging()

        self.tokens = nltk.word_tokenize(' '.join(self.words))
        self.tagged = nltk.pos_tag(self.tokens)
        self.nouns = [word for word,pos in self.tagged \
                 if (pos == 'NN' or pos == 'NNP' or pos == 'NNS' or pos == 'NNPS')]
        self.nouns = [x.lower() for x in self.nouns]
        self.merge()


    #TODO Bhavesh
    def operatorTagging(self):
        print "Start the operator tagging "# plus,add,sum,addition:+
        for i in range(len(self.phrases_1_size_operator)):
            operatorPhrase=self.phrases_1_size_operator[i]  #this will give me the phrase. greater than the
            self.tagged_operators.append('')
            for key in self.operatorMapping: #we want to avoid the last character
                    text=" ".join(str(x) for x in operatorPhrase)
                    text=text+' all'
                    key1=key[0]
                    b=self.match(key1,text,0.7)
                    if b==True:
                        #print "*********",self.opertorDictionary[j][-1]
                        self.tagged_operators[i]=key[-1]
                        break
        print "Tagged operator array ",self.tagged_operators
        print self.words

    #TODO Avinash
    def operandTagging(self):
        print "Start the operand tagging"
        for i in range(len(self.words)):
            self.tagged_operands.append('')

        for i in range(len(self.phrases_k_size)):  #k size phrases in a sentence
            phrase=self.phrases_k_size[i]
            phrase=' '.join(phrase)
            for dictionaryWordArr in self.operandDictionary:  #each line can have several similar meaning words
                text1=dictionaryWordArr[0].split('_')
                text1=' '.join(text1)
                b=self.match(phrase,text1,0.9)
                if b==True:
                    self.tagged_operands[i]=dictionaryWordArr[0]
        print "Tagged operand array ",self.tagged_operands
        print self.words

    def merge(self):
        self.merger=[]
        prevWasOperator=False
        prevWasOperand=False
        prevOperatorIndex=-1
        prevWasOperandIndex=-1
        for i in range(0,len(self.words)):
            operand=self.tagged_operands[i]
            operator=self.tagged_operators[i]
            self.merger.append('')
            if operand=='' and operator=='': #check if any variable name associated, nouns are important
                if self.words[i].lower() in self.nouns:
                    self.merger[i]=self.words[i]

            if operand=='' and operator=='':
                if self.words[i].isdigit():
                    self.merger[i]=self.words[i]

            if operator=='' and operator=='':
                if self.words[i].lower()=='by':
                    if prevOperatorIndex>=0 and  self.merger[prevOperatorIndex]=='>' or self.merger[prevOperatorIndex]=='>=':
                        self.merger[i]='+'
                        self.merger[prevOperatorIndex]='='
                        prevOperatorIndex=i
                    elif prevOperatorIndex>=0 and self.merger[prevOperatorIndex]=='<' or self.merger[prevOperatorIndex]=='<=':
                        self.merger[i]='-'
                        self.merger[prevOperatorIndex]='='
                        prevOperatorIndex=i


            if prevWasOperand==False and prevWasOperator==False:
                if operand!='' and len(operand)>=1:
                    self.merger[i]=operand
                    prevWasOperand=True
                    prevWasOperator=False
                    prevWasOperandIndex=i

            if prevWasOperand:
                if operator!='' and len(operator)>=1:
                    self.merger[i]=operator
                    prevWasOperator=True
                    prevWasOperand=False
                    prevOperatorIndex=i
            if prevWasOperator:
                if operand!='' and len(operand)>=1:
                    self.merger[i]=operand
                    prevWasOperator=False
                    prevWasOperand=True
                    prevWasOperandIndex=i
        print self.merger #all singly occurring words are nouns, merge all before and after any operator
        self.convertToScietific()
        print self.expression

    def convertToScietific(self):
        self.expression=''
        prevWasOperator=False
        prevWasOperand=False
        prevWasNoun=False
        for i in range(0,len(self.merger)):
            word=self.merger[i]
            if word in self.operands:   #means its an operand
                if prevWasOperand==False:
                    if prevWasNoun==True:
                        self.expression=self.expression+')'
                        prevWasNoun=False
                    self.expression=self.expression+' '+word
                    prevWasOperand=True
                    prevWasOperator=False
            elif word in self.operators:
                if prevWasOperator==False:
                    if prevWasNoun==True:
                        self.expression+=')'
                        prevWasNoun=False
                    self.expression+=' '+word
                    prevWasOperator=True
                    prevWasOperand=False
            elif word.lower() in self.nouns:
                if prevWasNoun==False:  #we can add a bracket and start writing the name
                    self.expression+='('+word.upper()
                    prevWasNoun=True
                elif prevWasNoun==True:
                    self.expression+=' '+word.upper()
                    prevWasNoun=True
            else:
                self.expression+=' '+word
        if prevWasNoun==True:
            self.expression+=')'


    def match(self,phrases,word_splits,threshold):
        if phrases==None or word_splits==None or len(phrases)==0 or len(word_splits)==0:
            return False
        text1=''
        text2=''
        for w1 in phrases:
            if len(w1)!=0 and w1!='[]':
                text1=w1+" "+text1
        for w2 in word_splits:
            if len(w2)!=0 and w2!='[]':
                text2=w2+" "+text2

        try:
            sim=self.cosineSim.cosine_sim(text1,text2)
        except:
            print text1, text2
            sim=self.cosineSim.cosine_sim(text1,text2)
            pass
        #print "similarity between", text1, text2, sim
        if sim>threshold:
            #print phrases, " and ",word_splits,"  matches"
            return True
        #print phrases, " and ",word_splits,"  dont match"
        return False





