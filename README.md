# Microorganism Search Engine

## Abstract
Matrix-Assisted Laser Desorption/Ionization Time-of-Flight (MALDI-TOF) is a soft ionization technique used in mass spectrometry to generate protein mass spectra of unknown microorganisms. By comparing the peaks observed in the spectrum and the sequences of microorganism ribosomal proteins, it provides a quick and inexpensive method for microorganism identification. Previous studies proposed a match scoring algorithm based on counting the number of spectral peaks matching protein sequences of microorganisms from a reference database and demonstrate the effectiveness and robustness of this tecnique with E.coli and B. subtilis. In our study, we addressed the lack of a public available tool implementing this algorithm and present a web-based user interface for rapid microorganism identification.

The core algorithm was implemented in Python based on FASTA files downloaded from UniProt and executed it on Linux command line. A web-based user interface was then implemented, using Turbogears1.5, a pythonic framework for web development. A number of features were added to the web-application to improve its utility, including user accounts and previously executed identification queries. Lastly, the scoring algorithm was integrated with the web-based user interface and the user-interface configured to execute queued queries asynchronously.

The web-application was tested with MALDI spectra of known microorganisms from Pineda et al. (2000), successfully demonstrating a public facing multi-user web-application for rapid microorganism identification.

## Start
```
git clone https://github.com/jinmingda/MicroorganismSearchEngine.git
cd MicroorganismSearchEngine
python start-mse.py
```
Open `localhost:8080` on browser

