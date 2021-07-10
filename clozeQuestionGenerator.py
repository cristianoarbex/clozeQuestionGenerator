# TODO
#
# Add other latex text highlighters such as \emph{} or \texttt{}


import sys
import numpy as np
import pandas as pd
import argparse
import os
import re
import time
from random import randint

parameterIdentifier = "@";
questionIdentifier  = "*";
latexBegin          = "\\(";
latexEnd            = "\\)";


##############################################################################
### Auxiliary functions
def stop(msg):
    print("");
    sys.exit("Error: " + msg);
# end stop
##############################################################################


##############################################################################
### Argument parsing
class CleanParser(argparse.ArgumentParser):
    def error(self, _):
        self.print_help()
        sys.exit(2)

parser = CleanParser(description='This script creates a Cloze question in Moodle XML format');
parser.add_argument('input', type=str, help='The input file name, must be in the correct format.');
parser.add_argument('output', type=str, help='Output must be a filename with extension .xml');
args       = parser.parse_args();
inputFile  = args.input;
outputFile = args.output;
#############################################################################

if not outputFile.endswith(".xml"):
    stop("Output file must end with .xml");


#####################################
### Default values
numParameters  = 0;
numQuestions   = 0;
categoryName   = "";
questionName   = "";
variantPenalty = 0;
questionText   = "";
variants       = np.empty([0], dtype = str  );
weights        = np.empty([0], dtype = int);
tolerance      = np.empty([0], dtype = float);
questions      = np.empty([0], dtype = str  );

###########################################################################
### Reading the input file
print("Reading the input file %s" % inputFile);
rFile = open(inputFile, encoding="UTF-8");
lines = rFile.readlines();
rFile.close();

insideQuestionText = 0;
insideVariants     = 0;
tempQuestionText = np.empty([0], dtype = str);
for i in range(len(lines)):
    lines[i] = lines[i].strip();
    if not insideQuestionText and lines[i] == "": continue;
    if lines[i].startswith("#"): continue;

    temp = lines[i].split();
    
    if insideQuestionText == 0:
        if temp[0] == "CategoryName":
            categoryName = " ".join(temp[1:len(temp)]);
        # end if

        if temp[0] == "QuestionName":
            questionName = " ".join(temp[1:len(temp)]);
        # end if
    
        if temp[0] == "QuestionWeights":
            for j in range(1, len(temp)):
                try:
                    f = int(temp[j]);
                    if (f <= 0):
                        stop("In QuestionWeights all weights must be positive.");
                    # end if
                    weights = np.append(weights, f);
                except ValueError:
                    stop("In QuestionWeights, the value %s is not a valid integer number. This is a Moodle limitation, weights must be integers." % temp[j]);
                # end try except
            # end for
        # end if

        if temp[0] == "VariantPenalty":
            if len(temp) != 2:
                stop("If VariantPenalty is defined, it must be followed by a single value only.");
            # end if
            try:
                f = int(temp[1]);
                if (f < 0):
                    stop("In VariantPenalty, the penalty must be a nonnegative number.");
                # end if
                variantPenalty = f;
            except ValueError:
                stop("In VariantPenalty, the value %s is not a valid integer number. It must be a percentage" % temp[1]);
            # end try except
        # end if
        

        if temp[0] == "Tolerance":
            if len(temp) == 1:
                stop("Parameter Tolerance was defined but no value was given.");
            # end if
            for j in range(1, len(temp)):
                try:
                    f = float(temp[j]);
                    if (f < 0):
                        stop("In Tolerance, all values must be nonnegative.");
                    # end if
                    tolerance = np.append(tolerance, f);
                except ValueError:
                    stop("In Tolerance, value %s is not a valid float number." % temp[j]);
                # end try except
            # end for
        # end if
    # end if
    

    if len(temp) > 0:
        if temp[0] == "EndQuestionText": 
            if len(temp) > 1:
                stop("The line containing the tag EndQuestionText must have only the tag and nothing else.");
            if insideQuestionText == 0:
                stop("Tag EndQuestionText was found before tag QuestionText.");
            insideQuestionText = 0;
        # end if
    # end if

    if insideQuestionText:
        tempQuestionText = np.append(tempQuestionText, lines[i]);
    # end if

    
    if len(temp) > 0:
        if temp[0] == "QuestionText":
            if len(temp) > 1:
                stop("The line containing the tag QuestionText must have only the tag and nothing else.");
            insideQuestionText = 1;
        # end if
    # end if 




    if len(temp) > 0:
        if temp[0] == "EndVariants": 
            if len(temp) > 1:
                stop("The line containing the tag Variants have only the tag and nothing else.");
            if insideVariants == 0:
                stop("Tag EndVariants was found before tag Variants.");
            insideVariants = 0;
        # end if
    # end if

    if insideVariants:
        variants = np.append(variants, lines[i]);
    # end if

    
    if len(temp) > 0:
        if temp[0] == "Variants":
            if len(temp) > 1:
                stop("The line containing the tag Variants must have only the tag and nothing else.");
            insideVariants = 1;
        # end if
    # end if 

# end for
###########################################################################

###########################################################################
### Error checking

if len(parameterIdentifier) != 1:
    stop("Variable parameterIdentifier must be a single character.");

if len(questionIdentifier) != 1:
    stop("Variable parameterIdentifier must be a single character.");

if categoryName == "":
    stop("CategoryName was not defined.");

if " /" in categoryName or "/ " in categoryName:
    stop("In the category name you provided, there cannot be a space before or after a slash (/)");

if "\\" in categoryName:
    stop("In the category name you provided, there cannot be backslash (\\)");

if questionName == "":
    stop("QuestionName was not defined.");

if "/" in questionName or "\\" in questionName:
    stop("In the question name you provided, there cannot be a slash (/) or backslash (\\)");

if len(tempQuestionText) == 0:
    stop("Question text was not found, perhaps tag QuestionText is missing.");

if insideQuestionText == 1:
    stop("End of question text was not found, tag EndQuestionText is missing.");

if insideVariants == 1:
    stop("End of variants was not found, tag EndVariants is missing.");

if len(variants) == 0:
    stop("Question must have at least one variant containing the numbers separated by space, inside the tag Variants ... EndVariants");

###########################################################################


###########################################################################
### Parse question text, process latex and parameters

questionText = "<p>"
for i in range(len(tempQuestionText)):
    # Ignore first empty lines of question
    if tempQuestionText[i] == "" and questionText == "<p>":
       continue; 
       
    if tempQuestionText[i] == "":
        questionText += "<br></p><p></p><p>";
    else:
        questionText += tempQuestionText[i]; 
# end for
questionText += "</p>"

temporaryDollarSignal = "DOLLARSIGNALREPLACE";


# To use a symbol $ in the question text, it must be preceded by \
if temporaryDollarSignal in questionText:
    stop("% is a reserved word, cannot be used in questionText" % temporaryDollarSignal);
questionText = re.sub("\\\\\$", temporaryDollarSignal, questionText);

if "$$" in questionText:
    stop("Latex in questionText must start with a single $, double $$ is not allowed.");

numLatexTags = questionText.count("$");

if numLatexTags % 2 != 0:
    stop("In the questionText there are an odd number of $. All latex symbols in questionText must start with a single $, double $$ is not allowed.");

questionText2 = "";
counter = 0;
for c in questionText:
    if c == parameterIdentifier:
        numParameters += 1;
    elif c == questionIdentifier:
        numQuestions += 1;
        
    if c == "$" and counter % 2 == 0:
        questionText2 += latexBegin;
        counter += 1;
    elif c == "$" and counter % 2 == 1:
        questionText2 += latexEnd;
        counter += 1;
    else:
        questionText2 += c;
# end for
questionText = questionText2;

questionText = re.sub(temporaryDollarSignal, "$", questionText);

if numQuestions == 0:
    stop("Question text must have at least one question with identifier %s" % questionIdentifier);

###########################################################################


###########################################################################
### Deal with bold and italics in Latex
questionText = re.sub("\\\\textbf{", "<b>", questionText);
questionText = re.sub("{\\\\bf",     "<b>", questionText);
questionText = re.sub("\\\\textit{", "<i>", questionText);
questionText = re.sub("{\\\\it",     "<i>", questionText);

replaceWith = np.array([], dtype = str);
replacePos  = np.array([], dtype = int);

# Bold
bold = [m.start() for m in re.finditer('<b>', questionText)];
if len(bold) > 0:
    replacePos  = np.append(replacePos,  bold);
    replaceWith = np.append(replaceWith, np.repeat("</b>", len(bold)));
# end if

# Italics
italics = [m.start() for m in re.finditer('<i>', questionText)];
if len(italics) > 0:
    replacePos  = np.append(replacePos,  italics);
    replaceWith = np.append(replaceWith, np.repeat("</i>", len(italics)));
# end if

replaceWith = replaceWith[np.argsort(replacePos)];
replacePos  = np.sort(replacePos);

for i in range(len(replacePos)-1, -1, -1):
    pos = questionText[replacePos[i]:len(questionText)].find("}");
    if (pos == -1):
        stop("In your latex code, there is a command missing a } (like \\textbf{ or \\textit{)");
    questionText = questionText[0:(replacePos[i]+pos)] + replaceWith[i] + questionText[(replacePos[i]+pos+1):len(questionText)]
# end for

###########################################################################


###########################################################################
### Assign weights and check consistency with the number of questions

# Set equal weights if no QuestionWeights in file
if len(weights) == 0:
    weights = np.repeat(1, numQuestions);
    #weights = weights.round(5);
    #weights[len(weights)-1] += 1 - sum(weights);
# end if

if numQuestions == 1 and weights[0] != 1:
    stop("If only one question is defined, its weight must be one.");

if len(weights) != numQuestions:
    stop("The number of question weights defined with tag QuestionWeights is not equal to the number of questions found in the question text.");
###########################################################################


###########################################################################
### Check validity of variants values
for i in range(len(variants)):
    values = variants[i].split();
    if len(values) != numParameters + numQuestions:
        stop("There are %d parameters and %d questions, so there should be %d values in each variant. Variant %d has only %d." % (numParameters, numQuestions, numParameters + numQuestions, i+1, len(values)));
    # end if

    for j in range(len(values)):
        try:
            float(re.sub(",", ".", values[j]));
        except ValueError:
            stop("In variant %d, the value %s is not numerical", i, values[j]);
        # end try except
    # end for
# end for
###########################################################################



###########################################################################
### Assign proper tolerance
if len(tolerance) == 0:
    counter = 0;
    for c in questionText:
        if c == parameterIdentifier:
            counter += 1;
        elif c == questionIdentifier:
            maxDecimals = 0;
            for j in range(len(variants)):
                values = variants[j].split();
                v = re.sub(",", ".", values[counter]);
                if "." in v:
                    v = v.split(".")[1];
                    if len(v) > maxDecimals:
                        maxDecimals = len(v);
                    # end if
                # end if
            # end for
            tol = "0"
            if maxDecimals > 0:
                tol += "." + "".join(np.repeat("0", maxDecimals-1)) + "1";
            # end if
            tolerance = np.append(tolerance, float(tol));
            counter += 1;
        # end if
    # end for
elif len(tolerance) == 1:
    tolerance = np.repeat(tolerance[0], numQuestions);
elif len(tolerance) != numQuestions:
    stop("The number of Tolerances defined is different from the number of questions.");
# end if
###########################################################################


###########################################################################
### Produce the questionText of each variant

for i in range(len(variants)):
    values = variants[i].split();
    question = "";
    
    counter = 0;
    qCounter = 0;
    for c in questionText:
        if c == parameterIdentifier:
            question += values[counter];
            counter += 1;
        elif c == questionIdentifier:
            cloze = " {" + str(weights[qCounter]) + ":NUMERICAL:%100%" + re.sub(",", ".", values[counter]) + ":" + str(tolerance[qCounter]);
            if variantPenalty > 0:
                for j in range(len(variants)):
                    if j == i:
                        continue;
                    # end if
                   
                    wrongValues = variants[j].split();
                    
                    if float(re.sub(",", ".", values[counter])) == float(re.sub(",", ".", wrongValues[counter])):
                        continue;
                    # end if
                    
                    cloze += "~%-" + str(variantPenalty) + "%" + re.sub(",", ".", wrongValues[counter]) + ":" + str(tolerance[qCounter]);
                # end for
            # end if
            cloze += "} ";
            
            question += cloze;
            counter += 1;
            qCounter += 1;
        else:
            question += c;
        # end if
    # end for
    questions = np.append(questions, question);
    
    #print("");
    #print(questions[i]);
# end for
###########################################################################

###########################################################################
### Produce output file

initialNumber = randint(5000, 200000);
output = """<?xml version="1.0" encoding="UTF-8"?>
<quiz>

<!-- question: 0  -->
  <question type="category">
    <category>
"""
output += "     <text>" + categoryName + "</text>";

output += """
    </category>
    <info format="html">
      <text></text>
    </info>
    <idnumber></idnumber>
  </question>
"""

for i in range(len(questions)):
    output += """

""";
    output += "<!-- question: " + str(initialNumber) + "  -->"
    output += """
  <question type="cloze">
    <name>    
    """
    output += "<text>" + questionName; 
    if len(questions) > 1: output += " V." + str(i+1);
    output += "</text>";
    output += """
    </name>
    <questiontext format="html">
    """;
    
    output += "<text><![CDATA[" + questions[i] + "]]></text>";

    output += """
    </questiontext>
    <generalfeedback format="html">
      <text></text>
    </generalfeedback>
    <hidden>0</hidden>
    <idnumber></idnumber>
  </question>    
    """
    
    initialNumber += 10
# end for

output += """
</quiz>
"""

text_file = open(outputFile, "w")
text_file.write(output)
text_file.close();
###########################################################################

#print(weights);
#print(variantPenalty);
#print(questionText);
#print(numParameters);
#print(numQuestions);
#print(variants);

print(output);

