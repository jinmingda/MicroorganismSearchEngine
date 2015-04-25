from collections import defaultdict
from Bio import SeqIO
import os.path


def readInput(spectrum):
    """Read the input from textbox and convert them to float type

    """

    return map(float, spectrum.strip().split("\t"))


def SelectFastaFile(database):
    if database == "Ribosomal Proteins in Bacteria: Reviewed":
        return "/RiboReviewed.fasta"
    elif database == "Ribosomal Proteins in Bacteria: Unreviewed":
        return "RiboUnreviewed.fasta"
    

def readOS(seqTitle):
    """Extract OS tag from sequence description

    Get the microorganism name from sequence title

    Args:
        seqTitle: SequenceObject.description

    Return
        Microorganism species name
    """

    i = 0
    x = seqTitle.find("=", i) + 1
    i = x + 1
    y = seqTitle.find("=", i) - 2
    #return seqTitle[x:y].strip()
    # Only takes the first two words from OS tag
    return " ".join(seqTitle[x:y].strip().split(None, 2)[:2])


def proteinMass(seq):
    """Calculate protein monoisotopic weight

    Args:
        seq: A protein sequence string, which might include selenocysteine(U)
        and pyrrolysine(O)

    Return:
        Protein monoisotopic weight including one water molecule

    Raise:
        KeyError when sequence contains ambiguous or unknown amino acids
    """

    from Bio.SeqUtils.ProtParam import ProteinAnalysis
    # The second argument in the ProteinAnalysis constructor indicates
    # the weight of the amino acids will be calculated using their
    # monoisotopic mass, if set to true
    return ProteinAnalysis(seq, True).molecular_weight()


def fastaFilter(fileName, lowerBound, upperBound):
    """Remove undesired sequences in the fasta file

    This function will remove the sequences whose molecular weight is
    either too high or too low, along with those containing amibugous
    amino acid characters.

    Args:
        fileName: Fasta file name
        lowerBound: The lower bound of protein weight
        upperBound: The upper bound of protein weight

    Return:
        An iterator of shrinked sequence objects

        iterator(SeqObject1, SeqObject2...)
    """
    directory = os.path.dirname(__file__)
    with open(directory+fileName, 'r') as fastaFile:
        for seqRecord in SeqIO.parse(fastaFile, "fasta"):
            # Use a try-except block to avoid illegal amino acid chars
            # including B, J, X, Z
            try:
                pMass = proteinMass(str(seqRecord.seq))
            except KeyError:
                continue
            if pMass >= float(lowerBound) and pMass <= float(upperBound):
                # Convert the function into an iterator
                # Yield is used like RETURN and will add item to the iterator
                yield seqRecord


def biomarker(sequence, mode):
    """Calculate biomarker under different mass spec modes

    Biomarker is protein's m/z value detected by mass spectrometry. Therefore
    in MALDI-TOF, different mass spec mode would have different impact on
    protein weight and previous studies have reported the loss of N terminal
    Methionine, which could in turn effect protein's biomarker value.

    Args:
        sequence: A protein sequence string
        mode: Mass spec mode includiing Positive, Negative and Neutral

    Return:
        An array of one or two biomarker values. If sequence has a N-terminal
        methionine, then the array would be [withMet, withoutMet].

        [1131.0404, 1000.000] or [1000]
    """

    met = 131.0404  # Methionine's monoisotopic weight
    proton = 1.007825   # Proton's monoisotopic weight
    pMass = proteinMass(str(sequence))
    if mode == "Positive":
        biomarkerValue = pMass + proton
    elif mode == "Negative":
        biomarkerValue = pMass - proton
    # Peptide is likely to lost its starting Met in mass spectrometry.
    # Therefore, biomarkers with and without Met should be both considered.
    if sequence.startswith("M"):
        return [biomarkerValue, biomarkerValue-met]
    else:
        return [biomarkerValue]


def isMatch(peak, biomarker, tolerance):
    """Check if spectral peak matches protein biomarker

    Args:
        peak: Spectral peak obatained from experiment, float
        biomarker: An array of biomarker values
        tolerance: Maximal difference between experimental weight and
        theoretical one that could be considered a match. float

    Return:
        True / False
    """

    for each in biomarker:
        if abs(float(peak) - each) <= float(tolerance):
            return True
    return False


def resultTable(spectrum, filteredSequences, tolerance, mode):
    """Output result table for all the matches

    This function will find all the sequences that match each of the
    spectral peak and keep them in a hash table, which could be used to
    calculate the number of matching hits and p-value.

    Args:
        spectrum: A list of float numbers representing spectral peaks
        filteredSequences: An array of post-filtering sequence objects
        tolerance: See above
        mode: See above

    Return:
        A dictionary of which key is the peak and value is a list of
        sequence objects that match the corresponding peak.

        {
            peak1: [SequenceObject1, SequenceObject3, SequenceObject5],
            peak2: [SequenceObject3, .......],
            ......
        }
    """

    hitDict = defaultdict(list)
    dbSize = defaultdict(int)  # Number of microorganism in the sequence file

    for seqRecord in filteredSequences:
        biomarkerValue = biomarker(str(seqRecord.seq), mode)
        microbeName = readOS(seqRecord.description)
        dbSize[microbeName] += 1
        for peak in spectrum:
            if isMatch(peak, biomarkerValue, tolerance):
                hitDict[peak].append(seqRecord)
    return hitDict, dbSize


def matchNum(hitResult):
    """Calculate the number of hit

    For each of the matching microorganism, calculate how many peaks in
    the unknown spectrum it has got.

    Args:
         Hash-table obtained by above function

    Return:
        A dictionary of microorganism-matches pair where microorganism
        name is the key and number of hits is the value

        {
            E.coli: 15,
            B.subtilus, 20,
            ...
        }
    """

    score = {}
    for matchList in hitResult.values():
        for bug in set(map(lambda x: readOS(x.description), matchList)):
            if bug in score:
                score[bug] += 1
            else:
                score[bug] = 1
    return score


def sortbyMatch(score):
    """Sort the result by number of matches in a descending order

    Args:
        score: A dictionary of microorganisms and match numbers obtained
        by above function

    Return
        A sorted list of key-value pairs
    """

    return sorted(score.items(), key=lambda x: x[1], reverse=True)


def pValue(bigK, k, n, nstar, bigN):
    """ Calculate p-value

    :param bigK: number of total peaks
    :param k: number of matching peaks
    :param n: number of proteins
    :param nstar: (maxMass - minMass) / (2 * tolerance)
    :param bigN: number of total microorganisms (trials)
    :return: p-value, e-value
    """

    from scipy import special
    import math

    # chooseln(N, k) = lg(N Choose k)
    # special.gammaln(x) = (x-1)!
    def chooseln(N, k): # N > k
        return special.gammaln(N+1) - special.gammaln(N-k+1) - special.gammaln(k+1)

    # pValue = sum(pValue(k)) = pValue(k) + pValue(k+1) + ... + pValue(K)
    nstar = float(nstar)  # nstar MUST be float
    pvalue = 0
    for kprime in range(k, bigK+1):
        # pValue(k) = K Choose k * e^(-(K-k)*n/nstar) * (1-e^(-n/nstar))^k
        # Use logarithm of pValue(k) to avoid arithmetic issues
        # Use exponentiation to gain pValue again
        pvalue += math.exp(chooseln(bigK, kprime) -
                          (bigK-kprime) * n / nstar +
                          kprime * math.log(1-math.exp(-n/nstar)))

    # eValue = pValue * num of trials
    evalue = pvalue * bigN
    return pvalue, evalue




