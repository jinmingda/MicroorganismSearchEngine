from myAlgorithms.ScoringAlgorithms import *
from turbogears.database import PackageHub
from datetime import datetime
from mse import model
import threading
import traceback

__connection__ = hub = PackageHub('mse')
cleanupLock = threading.Lock()


def MicroorganismIdentification():
    if not cleanupLock.acquire(False):
        return
    try:
        while True:
            try:
                s = model.SearchList.selectBy(status="Incomplete")[0]
            except IndexError:
                break

            hub.begin()
            s.status = 'Running'
            hub.commit()
            startTime = datetime.now()

            spectrum = readInput(s.query)
            db = SelectFastaFile(s.database)
            filteredSeqs = fastaFilter(db, s.min_mass, s.max_mass)
            result, dbSize = resultTable(spectrum, filteredSeqs, s.mass_tolerance, s.spec_mode)
            score = matchNum(result)
            output = sortbyMatch(score)
            for microbe, hit in output:
                bigK = len(spectrum)    # Number of peaks in the unknown spectrum
                k = hit                 # Number of peaks that match
                n = dbSize[microbe]     # Number of sequences in each microorganisms
                bigN = len(dbSize)      # Number of microorganisms in the sequence file
                nstar = (s.max_mass - s.min_mass) / (2 * s.mass_tolerance)

                pvalue, evalue = pValue(bigK, k, n, nstar, bigN)
                pvalue = float('%.3g' % pvalue)  # Trim the number of significant figure to 3
                evalue = float('%.3g' % evalue)
                model.ResultList(microorganism_name=microbe, matching_hit=hit,
                                 p_value=pvalue, e_value=evalue, search=s)

            s.status = 'Done'
            hub.commit()

            endTime = datetime.now()
            runningTime = endTime - startTime
            print runningTime
    except Exception, e:
        traceback.print_exc(e)
        raise
    finally:
        cleanupLock.release()
