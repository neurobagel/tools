# This file is adapted from https://github.com/neurobagel/bagel-cli/blob/main/bagel/mappings.py
# and contains only the mappings used for Neurobagel data dictionary validation.

from collections import namedtuple

Namespace = namedtuple("Namespace", ["pf", "url"])
NB = Namespace("nb", "http://neurobagel.org/vocab/")

NEUROBAGEL = {
    "participant": NB.pf + ":ParticipantID",
    "session": NB.pf + ":SessionID",
    "sex": NB.pf + ":Sex",
    "age": NB.pf + ":Age",
    "diagnosis": NB.pf + ":Diagnosis",
    "subject_group": NB.pf + ":SubjectGroup",
    "assessment_tool": NB.pf + ":Assessment",
}
