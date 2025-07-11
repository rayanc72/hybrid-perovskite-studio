
from diffpy.pdffit2 import PdfFit
import numpy as np
def calculate_pdf(
        diffpy_structure,
        diffpy_structure_attributes={"Uisoequiv": 0.01},
        pdf_calculator_kwargs={
            "qmin": 1,
            "qmax": 20,
            "rmin": 1.0,
            "rmax": 20.0,
            "qdamp": 0.06,
            "qbroad": 0.06
        }
):
    """Computes the PDF of the given structure.

    Parameters
    ----------
    structure : pymatgen.core.structure.Structure
        Materials structure.
    diffpy_structure_attributes : dict, optional
        Attributes to set on the diffpy structure object.
    pdf_calculator_kwargs : dict, optional
        Keyword arguments to pass to the diffpy PDF calculator.

    Returns
    -------
    numpy.ndarray
    """

    for key, value in diffpy_structure_attributes.items():
        setattr(diffpy_structure, key, value)

    # ## PDFCalculator is for diffpy.srreal and will be replaced by diffpy.pdffit2
    # dpc = PDFCalculator(**pdf_calculator_kwargs)
    # r1, g1 = dpc(diffpy_structure)

    pf = PdfFit()
    pf.alloc('X',
             pdf_calculator_kwargs['qmax'],
             pdf_calculator_kwargs['qdamp'],
             pdf_calculator_kwargs['rmin'],
             pdf_calculator_kwargs['rmax'],
             1800
             )
    pf.setvar(pf.qbroad, pdf_calculator_kwargs['qbroad'])
    pf.add_structure(diffpy_structure)
    pf.calc()

    r1 = np.asarray(pf.getR())
    g1 = np.asarray(pf.getpdf_fit())

    # return np.array([r1, g1]).T
    return r1, g1