import spacy

# Load the default spaCy model
nlp = spacy.load("en_core_web_sm")

def extract_nested_relationships(phrase):
    """Extract nested entity-predicate-object structures within a phrase."""
    relationships = []
    for token in phrase:
        if token.dep_ == "prep":  # Check for prepositions within the phrase
            # Entity is the head of the preposition (e.g., 'theory')
            entity = token.head
            # Object is the object of the preposition (e.g., 'relativity')
            obj = next((child for child in token.children if child.dep_ == "pobj"), None)
            if entity and obj:
                relationships.append({
                    "entity": entity.text,
                    "predicate": token.text,
                    "object": obj.text
                })
    return relationships

def extract_relationships(text):
    doc = nlp(text)
    relationships = []

    for sentence in doc.sents:
        for token in sentence:
            if token.pos_ == "VERB":
                subject = None
                obj = None

                for child in token.children:
                    if child.dep_ in ("nsubj", "nsubjpass"):
                        subject = child
                    if child.dep_ in ("dobj", "attr", "prep", "pobj"):
                        obj = child

                if subject and obj:
                    relationships.append({
                        "subject": subject.text,
                        "predicate": token.text,
                        "object": ' '.join([t.text for t in obj.subtree])
                    })

                    # Extract nested relationships within the object phrase
                    nested_rels = extract_nested_relationships(obj.subtree)
                    relationships.extend(nested_rels)

    return relationships

# Sample input text
text = """Alan Mathison Turing OBE FRS 23 June 1912 – 7 June 1954) was an English mathematician, computer scientist, logician, cryptanalyst, philosopher and theoretical biologist.[5] He was highly influential in the development of theoretical computer science, providing a formalisation of the concepts of algorithm and computation with the Turing machine, which can be considered a model of a general-purpose computer.[6][7][8] Turing is widely considered to be the father of theoretical computer science.[9]

Born in London, Turing was raised in southern England. He graduated from King's College, Cambridge, and in 1938, earned a doctorate degree from Princeton University. During World War II, Turing worked for the Government Code and Cypher School at Bletchley Park, Britain's codebreaking centre that produced Ultra intelligence. He led Hut 8, the section responsible for German naval cryptanalysis. Turing devised techniques for speeding the breaking of German ciphers, including improvements to the pre-war Polish bomba method, an electromechanical machine that could find settings for the Enigma machine. He played a crucial role in cracking intercepted messages that enabled the Allies to defeat the Axis powers in many crucial engagements, including the Battle of the Atlantic.[10][11]

After the war, Turing worked at the National Physical Laboratory, where he designed the Automatic Computing Engine, one of the first designs for a stored-program computer. In 1948, Turing joined Max Newman's Computing Machine Laboratory at the Victoria University of Manchester, where he helped develop the Manchester computers[12] and became interested in mathematical biology. Turing wrote on the chemical basis of morphogenesis[13][1] and predicted oscillating chemical reactions such as the Belousov–Zhabotinsky reaction, first observed in the 1960s. Despite these accomplishments, he was never fully recognised during his lifetime because much of his work was covered by the Official Secrets Act.[14]

In 1952, Turing was prosecuted for homosexual acts. He accepted hormone treatment, a procedure commonly referred to as chemical castration, as an alternative to prison. Turing died on 7 June 1954, aged 41, from cyanide poisoning. An inquest determined his death as suicide, but the evidence is also consistent with accidental poisoning.[15] Following a campaign in 2009, British prime minister Gordon Brown made an official public apology for "the appalling way [Turing] was treated". Queen Elizabeth II granted a pardon in 2013. The term "Alan Turing law" is used informally to refer to a 2017 law in the UK that retroactively pardoned men cautioned or convicted under historical legislation that outlawed homosexual acts.[16]

Turing left an extensive legacy in mathematics and computing which today is recognised more widely, with statues and many things named after him, including an annual award for computing innovation. His portrait appears on the Bank of England £50 note, first released on 23 June 2021 to coincide with his birthday. The audience vote in a 2019 BBC series named Turing the greatest person of the 20th century."""


# Extract relationships from the text
relationships = extract_relationships(text)

# Print out relationships in JSON format
import json
print(json.dumps(relationships, indent=2))