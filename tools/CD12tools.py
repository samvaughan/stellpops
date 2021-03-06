import numpy as np
import pylab as pl
import pdb
from stellarpops.tools import specTools as ST
import scipy.constants as const
from scipy import interpolate
from os.path import expanduser
import glob
import scipy.interpolate as si

cd12tools_basedir="/Data/stellarpops"

L_sun = 3.826E33 # the L_sun defined by BC03 in erg/s

def loadCD12ssps(sedpath=cd12tools_basedir+"CvD12_v1.2", ageglob="t??.?_solar.ssp", massfile="mass_ssp.dat", model="CD12", Z=0.02, verbose=True):
    """
    Author:  Ryan Houghton (18/09/12)

    Purpose: Load one of the Conroy / van Dokkum Z=SOLAR, varying age, SSP models, keeping:
       - IMF (string)
       - Age (Gyr)
       - Metallicity Z
       - Wavelength (AA)
       - Flux density (erg/s/AA/cm^2)
    
    """
    # get the AGE files to read in
    afiles, nafiles = ST.findfiles(expanduser(sedpath)+"/"+ageglob)

    # get mass info
    minfo = at.Table(expanduser(sedpath)+"/"+massfile, type="ascii")
    imftags = minfo.col1
    masses = np.array([minfo.col2, minfo.col3, minfo.col4, minfo.col5, minfo.col6, minfo.col7])

    # convert: L_sun/micron => * L_sun[erg/s] / 1e4 / (4.*pi*D[cm]**2) => erg/s/cm**2/AA (@10pc)
    factor= (L_sun/1e4/(10.0*ST.pc*100.0)**2.0) / (4.0*np.pi)

    # read SSP files one by one
    ages=[]
    Zs=[]
    imfs=[]
    flux1=[]
    flux2=[]
    flux3=[]
    flux4=[]
    flux5=[]
    wave=None
    for f in afiles:
        # load table
        ssp  = at.Table(f, type='ascii')
        # get age of file
        ages.append(float(f[-14:-10]))
        # get metallicity
        Zs.append(Z)
        # get imfs of fluxes
        imfs.append(imftags) 
        # get wave (once)
        if wave==None: wave = ssp.col1
        # get fluxes for each IMF
        flux1.append(ssp.col2*factor)
        flux2.append(ssp.col3*factor)
        flux3.append(ssp.col4*factor)
        flux4.append(ssp.col5*factor)
        flux5.append(ssp.col6*factor)
        if verbose: print("Loaded "+f)


    flux=[]
    flux.append(np.array(flux1))
    flux.append(np.array(flux2))
    flux.append(np.array(flux3))
    flux.append(np.array(flux4))
    flux.append(np.array(flux5))
    # now make spectra for age variations, one for each IMF
    specs=[]
    for q in range(5):
        spec = ST.spectrum(lamspec=flux[q], lam=wave, age=ages, mass=masses[:,q], \
                          Z=Zs[q], IMF=imftags[q], model=model, wavesyst="vac")
        specs.append(spec)

    return specs

def loadCD12varelem(basedir=cd12tools_basedir):
    """
    RH 28/10/2016
    Load the CvD spectra with varyine element abundances.
    """
    return loadCD12spec(basedir+"/CvD1.2/"+"t13.5_varelem.ssp")

def loadCD12afe(basedir=cd12tools_basedir):
    """
    RH 1/11/2016
    Load the CvD spectra with varying [alpha/Fe]
    """
    s02 = loadCD12spec(basedir+"/CvD1.2/"+"t13.5_afe+0.2.ssp")
    s03 = loadCD12spec(basedir+"/CvD1.2/"+"t13.5_afe+0.3.ssp")
    s04 = loadCD12spec(basedir+"/CvD1.2/"+"t13.5_afe+0.4.ssp")
    return [s02,s03,s04]

def load_all_CD12spec(base_dir=cd12tools_basedir, folder="CvD1.2", verbose=True):
    """
    SPV 9/01/17
    Load all CvD 12 spectra and save them as a dictionary, with their filenames as the keys (without the '.ssp' part)
    """

    import glob
    import os

    cvd_list=glob.glob('{}/{}/*.ssp'.format(base_dir, folder))

    if verbose:
        print 'Opening files in {}/{}'.format(base_dir, folder)

    all_specs={}

    for file in cvd_list:
        if verbose:
            print 'Loading {}'.format(file)
        fname=os.path.basename(file)[:-4]
        all_specs[fname]=loadCD12spec(file)

    return all_specs

def loadCD12spec(filepath):
    """
    Originally written by Simon Zieleniewski.
    Adapted by Ryan Houghton. 

    Function to read in CvD12 SSP files and return spectra as a
        spectrum class (created by RCWH).

    Inputs:
    =======
    - filepath: Path and filename string of file for CvD spectra

    Outputs:
    ========
    - spectrum: A spectrum class for the given SSP SED.
                Initialised with units (lambda=A, flux=erg/s/cm2/A) @ D=10pc


    e.g
    
    csalpha= loadCD12spec(basedir+"CvD12_v1.2/t13.5_varelem.ssp")
    csabun = loadCD12spec(basedir+"CvD12_v1.2/t13.5_varelem.ssp")

    """  

    dat = np.genfromtxt(filepath)

    #Get filename
    fname = filepath.split('/')[-1]

    #Wavelenghts in A
    lambs = dat[:,0].copy()

    #Set flux units to erg/s/cm**2/A at D = 10 pc. CvD flux in units of L_sun/um
    flux = np.transpose(dat[:,1:].copy())
    factor = (L_sun/1e4/(10.0*ST.pc*100.0)**2.0) / (4.0*np.pi)
    flux *= factor

    #Age of spectra in Gyrs
    Age = [float(fname.split('_')[0].split('t')[1])]*flux.shape[0]
    

    #Interpolate to get linear dispersion
    newlambs = np.linspace(lambs[0], lambs[-1], len(lambs))
    finterp = interpolate.interp1d(lambs, flux, kind='linear', axis=-1)
    newflux = finterp(newlambs)

    #Get mass file
    masspath = filepath.split(fname)[0]
    masses_orig = np.loadtxt(masspath+'mass_ssp.dat', dtype=np.str)
    masses = np.copy(masses_orig)
    masspos = {13.5:6, 11.0:5, 9.0:4, 7.0:3, 5.0:2, 3.0:1}
    mass = np.array(masses[:,masspos[Age[0]]], dtype=np.float)

    #Depending on filename, spectra correspond to different IMFs, ages etc
    if 'solar' in fname:
        #IMFs = x=3.5, 3.0, 2.35, Chabrier, bottom-light
        IMFs = ['x = 3.5', 'x = 3.0', 'x = 2.35', 'Chabrier', 'bottom-light']
        return ST.spectrum(lamspec=newflux, lam=newlambs, age=Age,
                          Z=0.2, IMF=IMFs, model='CD12', mass=mass, wavesyst="vac")

    if 'afe' in fname:
        met = 0.0
        IMFs = ['x = 3.5', 'x = 3.0', 'x = 2.35', 'Chabrier', 'bottom-light']
        afes = {'afe': float(fname.split('+')[1][0:3])}
        return ST.spectrum(lamspec=newflux, lam=newlambs, age=Age, alpha=afes['afe'], 
                          Z=met, IMF=IMFs, model='CD12', 
                          mass=mass, wavesyst="vac") #userdict=afes,

    if 'varelem' in fname:
        IMF = 'Chabrier'
        uAge = list(set(Age))[0]
        met = 0.0
        massloc = np.where(masses[:,0]==IMF)[0]
        masses = masses[massloc[0],1:]
        mass = float(masses[masspos[uAge]-1])
        
        abunlist = {'abundances': ['[Na/Fe] = +0.3', '[Na/Fe] = -0.3','[Ca/Fe] = +0.15', '[Ca/Fe] = -0.15',
                '[Fe/H] = +0.3', '[Fe/H] = -0.3', '[C/Fe] = +0.15', '[C/Fe] = -0.15',
                '[a/Fe] = +0.2', '[as/Fe] = +0.2', '[N/Fe] = +0.3', '[N/Fe] = -0.3',
                '[Ti/Fe] = +0.3', '[Ti/Fe] = -0.3', '[Mg/Fe] = +0.3', '[Mg/Fe] = -0.3',
                '[Si/Fe] = +0.3', '[Si/Fe] = -0.3']}
        return ST.spectrum(lamspec=newflux, lam=newlambs, age=Age,
                          Z=met, IMF=IMF, model='CD12', userdict=abunlist,
                          mass=mass, wavesyst="vac")

    else:
        raise ValueError('Did not input correct CD12 file [as of 03-04-14]')



################################################################################################################################################################################################
def load_base_CvD16ssps(dirname='/Data/stellarpops/CvD2/', folder='vcj_models', verbose=True):

    import os
    dirname=os.path.expanduser(dirname)

    vcj_models=sorted(glob.glob('{}/{}/VCJ_*.s100'.format(dirname, folder)))
    temp_lamdas, x35, x3, x23, kroupa, flat=np.genfromtxt(vcj_models[0], unpack=True)


    model_Zs_names=['m1.5', 'm1.0', 'm0.5', 'p0.0', 'p0.2']
    Zs=[-1.5, -1.0, -0.5, 0.0, 0.2]
    ages=[1.0, 3.0, 5.0, 7.0, 9.0, 11.0, 13.5]
    model_imfs_order=['x35', 'x3', 'x23', 'kroupa', 'flat']

    n_ages=len(ages)
    n_zs=len(Zs)
    n_imfs=len(model_imfs_order)

    
    spectra={}
    

    templates=np.empty( (n_imfs, n_ages, n_zs, len(x35)) )

    for a, Z in enumerate(model_Zs_names):

        for b, age in enumerate(ages):

            model=glob.glob('{}/{}/VCJ_*{}*{}.ssp.s100'.format(dirname, folder, Z, age))[0]
            if verbose:
                print 'Loading {}'.format(model)
            data=np.genfromtxt(model)

            for i, imf in enumerate(model_imfs_order):
                templates[i, b, a, :]=data[:, i+1]

    age_values=np.repeat(ages, len(Zs)).reshape(len(ages), len(Zs))
    Z_values=np.repeat(Zs, len(ages)).reshape(len(Zs), len(ages)).T


    
       
    for i, imf in enumerate(model_imfs_order):

        spectra[imf]=ST.spectrum(lam=temp_lamdas, lamspec=templates[i, :, :, :], age=age_values, IMF=imf, Z=Z_values, wavesyst='vac')

    return spectra


def load_varelem_CvD16ssps(dirname='/Data/stellarpops/CvD2', folder='atlas_rfn_v3', imf='kroupa', verbose=True):


    import os
    dirname=os.path.expanduser(dirname)

    if imf in ['kroupa', 'krpa', 'Kroupa', 'Krpa']:
        model_spectra=sorted(glob.glob('{}/{}/atlas_ssp_*.krpa.s100'.format(dirname, folder)))
        imf_name='krpa'
    elif imf in ['Salpeter', 'salpeter', 'salp', 'Salp']:
        model_spectra=sorted(glob.glob('{}/{}/atlas_ssp_*.salp.s100'.format(dirname, folder)))
        imf_name='salp'
    else:
        raise NameError('IMF type not understood')
    
    
    data=np.genfromtxt(model_spectra[0])
    lams=data[:, 0]

    model_Zs_names=['m1.5', 'm1.0', 'm0.5', 'p0.0', 'p0.2']
    model_age_names=['01', '03', '05', '09', '13']

    model_elem_order=['Solar', 'Na+', 'Na-', 'Ca+', 'Ca-', 'Fe+', 'Fe-', 'C+', 'C-', 'a/Fe+', 'N+', 'N-', 'as/Fe+', 'Ti+', 'Ti-', 
    'Mg+', 'Mg-', 'Si+', 'Si-', 'T+', 'T-', 'Cr+', 'Mn+', 'Ba+', 'Ba-', 'Ni+', 'Co+', 'Eu+', 'Sr+', 'K+','V+', 'Cu+', 'Na+0.6', 'Na+0.9']


    Zs=[-1.5, -1.0, -0.5, 0.0, 0.2]
    ages=[float(a) for a in model_age_names]

    n_ages=len(model_age_names)
    n_zs=len(model_Zs_names)
    n_elems=len(model_elem_order)

    templates=np.empty( (n_elems, n_ages, n_zs, len(lams)) )

    for a, Z in enumerate(model_Zs_names):
        for b, age in enumerate(model_age_names):


            
            model=glob.glob('{}/{}/atlas_ssp*t{}*{}*{}.s100'.format(dirname, folder, age, Z, imf_name))[0]
            if verbose:
                print 'Loading {}'.format(model)
            data=np.genfromtxt(model)



            for i, elem in enumerate(model_elem_order):
                templates[i, b, a, :]=data[:, i+1]


    
    spectra={}
    for i, elem in enumerate(model_elem_order):

        
        age_values=np.repeat(ages, n_zs).reshape(n_ages, n_zs)
        Z_values=np.repeat(Zs, n_ages).reshape(n_zs, n_ages).T

        spectra[elem]=ST.spectrum(lam=lams, lamspec=templates[i, :, :, :], age=age_values, Z=Z_values, wavesyst='vac', userdict={'elem':elem})

    return spectra
    

def get_element_enhanced_spec(spec, element, enhancement=0.3, base_enhancement=0.3, varelem_dict=None, elem_param_dict=None, base_param_dict=None):

    """Take a CvD variable element spectrum and find its ratio with the solar abundance pattern spectrum. Apply this ratio as a response function to another spectrum.
    Enhancement should always be positive
    """

    if varelem_dict is None:
        if spec.IMF in ['flat', 'kroupa']:
            varelem_dict=load_varelem_CvD16ssps(imf='kroupa')
        elif spec.IMF in ['x35', 'x3', 'x23']:
            varelem_dict=load_varelem_CvD16ssps(imf='salp')
        else:
            raise NameError('IMF type not understood- check spectrum.IMF exists or load the varelem dictionary separately.')
    if elem_param_dict is None:
        elem_param_dict=CD16_get_np_indices_for_elems()
    if base_param_dict is None:
        base_param_dict=CD16_get_np_indices_for_params()


    assert enhancement>=0.0, 'Enhancement should always be positive. To make an under-enhanced spectrum, use Elem- with enhancement >0, e.g. Na-, +0.3'


    assert element in varelem_dict.keys(), 'Pick an element which is in the CvD variable element file'



    factor = (varelem_dict[element].flam/varelem_dict['Solar'].flam-1)*((10**(enhancement)-1.0)/(10**(base_enhancement)-1.0))


    #Bit of a hack: we want to select the ages from the original array which are also in the varying elemental abundance spectra: 1, 3, 5, 9, 13 but ignoring 7 and 11 Gyrs.    
    if spec.flam.shape !=factor.shape:
        age_axis_mask=np.array([True, True, True, False, True, False, True])
    else:
        age_axis_mask=np.ones(spec.flam.shape[0]).astype(bool)

    newspec=ST.spectrum(lam=spec.lam, lamspec=np.exp(np.log(spec.flam[age_axis_mask, :, :])+factor), age=spec.age[age_axis_mask, :], Z=spec.Z[age_axis_mask, :], IMF=spec.IMF, wavesyst='vac', userdict={'elem':element})

    return newspec 

def CD16_get_np_indices_for_elems(elems=['Solar', 'Na+', 'Na-', 'Ca+', 'Ca-', 'Fe+', 'Fe-', 'C+', 'C-', 'a/Fe+', 'N+', 'N-', 'as/Fe+', 'Ti+', 'Ti-', 
    'Mg+', 'Mg-', 'Si+', 'Si-', 'T+', 'T-', 'Cr+', 'Mn+', 'Ba+', 'Ba-', 'Ni+', 'Co+', 'Eu+', 'Sr+', 'K+','V+', 'Cu+', 'Na+0.6', 'Na+0.9'], Zs=[-1.5, -1.0, -0.5, 0.0, 0.2], ages=[1.0, 3.0, 5.0, 9.0, 13.0], verbose=False):
    

    param_dict={}


    elem_dict=dict(enumerate(elems))
    elem_dict=dict((v,k) for k,v in elem_dict.iteritems())    

    Z_dict=dict(enumerate(Zs))
    Z_dict=dict((v,k) for k,v in Z_dict.iteritems())

    age_dict=dict(enumerate(ages))
    age_dict=dict((v,k) for k,v in age_dict.iteritems())

    for d in [elem_dict, Z_dict, age_dict]:
        for k, v in d.iteritems():
            if verbose:  
                print k, v
            param_dict[k]=v

    return param_dict


def CD16_get_np_indices_for_params(IMFs=['x35', 'x3', 'x23', 'kroupa', 'flat'], \
    Zs=[-1.5, -1.0, -0.5, 0.0, 0.2], ages=[1.0, 3.0, 5.0, 7.0, 9.0, 11.0, 13.5], verbose=False):

    #We want a dictionary where we can get the index for any IMF, Z or age
    #e.g dictionary['bi0.30']=0, dict['m2.32']=0, dict['p0.22']=6, etc


    param_dict={}


    imf_dict=dict(enumerate(IMFs))
    imf_dict=dict((v,k) for k,v in imf_dict.iteritems())    

    Z_dict=dict(enumerate(Zs))
    Z_dict=dict((v,k) for k,v in Z_dict.iteritems())

    age_dict=dict(enumerate(ages))
    age_dict=dict((v,k) for k,v in age_dict.iteritems())

    
    for d in [imf_dict, Z_dict, age_dict]:
        for k, v in d.iteritems():
            if verbose:  
                print k, v
            param_dict[k]=v

    return param_dict





def CvD_cut_and_measure_index(spec, index, out_sigma, index_type='Simple', model_sigma=None, n_sig=10.0, verbose=False):

    """
    Use specTools to cut a long spectrum down to size and measure an index. CvD12v1.2 models have a resolving power of 2000 above 7500A, 
    a FWHM of 2.51A below. 
    """


    
    if out_sigma>0.0:
        if model_sigma is None: 

            if np.atleast_1d(np.array(index['red_stop']))[-1]<7500.0:

                if index['nfeat']>0.0:
                    model_sigma=const.c*2.5/(np.sqrt(8.*np.log(2.0))*index['ind_start'][0]*1000.0)
                else:
                    model_sigma=const.c*2.5/(np.sqrt(8.*np.log(2.0))*index['blue_stop']*1000.0)

            # assert out_sigma > model_sigma, 'Cant convolve to a resolution below the model resolution'
            # conv_sigma=np.sqrt(out_sigma**2 - model_sigma**2)
               
            else:
                model_sigma=const.c/(np.sqrt(8.*np.log(2.0))*2000*1000)

            assert out_sigma > model_sigma, 'Cant convolve to a resolution below the model resolution'
            conv_sigma=np.sqrt(out_sigma**2 - model_sigma**2)

        cutspec=ST.cutAndGaussVelConvolve(spec, index, conv_sigma, verbose=False, fix_uneven_lamdas=True, n_sig=n_sig)
    else:
        if verbose:
            print 'Not convolving the spectrum'
        cutspec=spec


    


    if index_type=='Cenarro':
        indvals=ST.calcCenarroIndex(cutspec, index)
    elif index_type=='Simple':
        indvals=ST.calcSimpleIndex(cutspec, index)
    else:
        raise TypeError('Index Type not understood')


    return indvals



def CD12_get_np_indices_for_params(IMFs=['x = 3.5', 'x = 3.0', 'x = 2.35', 'Chabrier', 'bottom-light'], \
    Zs=[0.00], ages=[3.0, 5.0, 7.0, 9.0, 11.0, 13.5], verbose=False):

    #We want a dictionary where we can get the index for any IMF, Z or age
    #e.g dictionary['bi0.30']=0, dict['m2.32']=0, dict['p0.22']=6, etc


    param_dict={}


    imf_dict=dict(enumerate(IMFs))
    imf_dict=dict((v,k) for k,v in imf_dict.iteritems())    

    Z_dict=dict(enumerate(Zs))
    Z_dict=dict((v,k) for k,v in Z_dict.iteritems())

    age_dict=dict(enumerate(ages))
    age_dict=dict((v,k) for k,v in age_dict.iteritems())

    
    for d in [imf_dict, Z_dict, age_dict]:
        for k, v in d.iteritems():
            if verbose:  
                print k, v
            param_dict[k]=v

    return param_dict







def calcM2L(filter, age, Z, imf, best_spec=None, z=0.0, bandcor=False, plot=False, change_units=True):

    """
    Given a spectrum with an age, Z and IMF, calculate its M/L ratio in a given filter.
    Assume we just want the visible here- if not, make sure you change the range of your
    templates to include the filter bandpass!
    """
    factor= (L_sun/1e4/(10.0*ST.pc*100.0)**2.0) / (4.0*np.pi)
    
    
    if best_spec is None:
        lam_range_temp=[3000, 11000]       
        from stellarpops.tools import fspTools as FT
        interp, lin_lams= FT.prepare_linear_CvD_interpolator(lam_range_temp, verbose=False)
        best_spec=ST.spectrum(lin_lams, interp((lin_lams, age, Z, imf))*factor)
    else:
        if change_units:
            best_spec=ST.spectrum(best_spec.lam, best_spec.flam*factor)
    m=get_mass_for_spec(age, Z, imf)

    sol = ST.loadHSTSolarSpec()
    lsun = sol.calcABmag(filter, z=z, bandcor=bandcor, plot=False)
    msun = 1.0

    l = best_spec.calcABmag(filter, z=z, bandcor=bandcor, plot=False)

    m2l = (m/10.0**(-0.4*l)) / (msun/10.0**(-0.4*lsun))

    return m2l

def get_mass_for_spec(age, metallicity, imf_slope, filename='CvD16_mass_file_initial_mass_with_remnants.dat', dirpath='/home/vaughan/Science/MIST_isochrones/CvD16_mass_files'):

    print 'getting the mass file from {}'.format(filename)
    mass_interp=make_mass_interpolator(filename=filename, dirpath=dirpath)

    return mass_interp((imf_slope, metallicity, age))

def CvD_IMF_shape(masses, mu, verbose=True):

    """
    CvD_IMF is a power law with slope 2.35>1 solar mass and slope mu below it.
    However it also has a Kroupa IMF, which we take as mu=1.8 and deal with separately.
    """

    if mu!=1.8:
        lower_section= masses[masses<1.0]**-mu
        upper_section= masses[masses>=1.0]**-2.3
        
    else:
        if verbose:
            print 'Assuming we want a Kroupa IMF'
        lowest_section= masses[masses<0.5]**-1.3
        middle_section= masses[(masses<=1.0) & (masses>=0.5)]**-2.3

        lower_section=np.concatenate((lowest_section, middle_section))

        upper_section= masses[masses>=1.0]**-2.3


    return np.concatenate((lower_section, upper_section))


def get_mass_from_iso(iso, age, low_mass_slope, mass_type='initial_mass', verbose=True, remnants=True):


    assert mass_type in ['initial_mass', 'star_mass'], 'Mass type must be one of "initial_mass" or "star_mass"'

    logage=np.log10(age*10**9)
    assert (logage>5.0) & (logage <10.3), "Age should be in Gyrs, and logAge must be between 5 and 10.3"

    age_ind=iso.age_index(logage) 
    masses=iso.isos[age_ind][mass_type]

    m_low, m_up=0.08, 100
    m=np.linspace(m_low, m_up, 100000)
    dm=np.mean(np.ediff1d(m))
    m0=np.trapz(m*CvD_IMF_shape(m, low_mass_slope, verbose=verbose), dx=dm)

    most_massive_alive_star=masses[-1]

    m_at_age=np.trapz(CvD_IMF_shape(m[m<most_massive_alive_star], low_mass_slope, verbose=verbose)*m[m<most_massive_alive_star], dx=dm)

    if remnants:
        #For the remnants, the standard equations that I think most people use are in Renzini & Ciotti (1993), Section 2.  

        # Notes from Charlie Conroy:

        # !BH remnants
        #     !40<M<imf_up leave behind a 0.5*M BH

        # !NS remnants
        #     !8.5<M<40 leave behind 1.4 Msun NS

        # !WD remnants
        #     !M<8.5 leave behind 0.077*M+0.48 WD
        remnants_mass_BH=np.trapz(m[m>40]*CvD_IMF_shape(m[m>40], low_mass_slope, verbose=verbose), dx=dm)*0.5

        remnants_mass_NS=np.trapz(CvD_IMF_shape(m[((m>8.5)&(m<40))], low_mass_slope, verbose=verbose), dx=dm)*1.4

        remnants_mass_WD=np.trapz(CvD_IMF_shape(m[((m>most_massive_alive_star) & (m<8.5))], low_mass_slope, verbose=verbose), dx=dm)*0.48 + \
            np.trapz(m[((m>most_massive_alive_star) & (m<8.5))]*CvD_IMF_shape(m[((m>most_massive_alive_star) & (m<8.5))], low_mass_slope, verbose=verbose), dx=dm)*0.077

        m_at_age+=remnants_mass_BH+remnants_mass_NS+remnants_mass_WD



    return m_at_age/m0


def make_mass_interpolator(filename='CvD16_mass_file_initial_mass_with_remnants.dat', dirpath='/home/vaughan/Science/MIST_isochrones/CvD16_mass_files'):



    low_mass_slopes=[0.0, 1.8, 2.3, 3.0, 3.5]
    ages=np.linspace(1e-3, 17, 100)
    metallicities=[-4.0, -3.0, -2.0, -1.0, -0.5, 0.0, 0.25, 0.5]

    data=np.genfromtxt('{}/{}'.format(dirpath, filename))
    masses=data.reshape(len(low_mass_slopes), len(metallicities), len(ages))


    mass_interp=si.RegularGridInterpolator((low_mass_slopes, metallicities, ages), masses)

    return mass_interp


def make_mass_text_file(mass_type='initial_mass', remnants=True):

    assert mass_type in ['initial_mass', 'star_mass'], 'Mass type must be one of "initial_mass" or "star_mass"'


    import read_mist_models as RM

    iso_m4=RM.ISO('/Data/MIST_isochrones/MIST_v1.0_vvcrit0.4_basic_isos/MIST_v1.0_feh_m4.00_afe_p0.0_vvcrit0.4_basic.iso')
    iso_m3=RM.ISO('/Data/MIST_isochrones/MIST_v1.0_vvcrit0.4_basic_isos/MIST_v1.0_feh_m3.00_afe_p0.0_vvcrit0.4_basic.iso')
    iso_m2=RM.ISO('/Data/MIST_isochrones/MIST_v1.0_vvcrit0.4_basic_isos/MIST_v1.0_feh_m2.00_afe_p0.0_vvcrit0.4_basic.iso')
    iso_m1=RM.ISO('/Data/MIST_isochrones/MIST_v1.0_vvcrit0.4_basic_isos/MIST_v1.0_feh_m2.00_afe_p0.0_vvcrit0.4_basic.iso')
    iso_m05=RM.ISO('/Data/MIST_isochrones/MIST_v1.0_vvcrit0.4_basic_isos/MIST_v1.0_feh_m0.50_afe_p0.0_vvcrit0.4_basic.iso')
    iso_p0=RM.ISO('/Data/MIST_isochrones/MIST_v1.0_vvcrit0.4_basic_isos/MIST_v1.0_feh_p0.00_afe_p0.0_vvcrit0.4_basic.iso')
    iso_p025=RM.ISO('/Data/MIST_isochrones/MIST_v1.0_vvcrit0.4_basic_isos/MIST_v1.0_feh_p0.25_afe_p0.0_vvcrit0.4_basic.iso')
    iso_p05=RM.ISO('/Data/MIST_isochrones/MIST_v1.0_vvcrit0.4_basic_isos/MIST_v1.0_feh_p0.50_afe_p0.0_vvcrit0.4_basic.iso')


    isos=[iso_m4,iso_m3,iso_m2,iso_m1, iso_m05,iso_p0, iso_p025, iso_p05]

    low_mass_slopes=[0.0, 1.8, 2.3, 3.0, 3.5]
    ages=np.linspace(1e-3, 17, 100)
    metallicities=[-4.0, -3.0, -2.0, -1.0, -0.5, 0.0, 0.25, 0.5]

    masses=np.empty((len(low_mass_slopes), len(metallicities), len(ages)))
    if remnants:
        print 'Making a mass grid including remnants'
    else:
        print 'Making a mass grid NOT including remnants'

    for k, slope in enumerate(low_mass_slopes):
        for i, iso in enumerate(isos):
            for j, age in enumerate(ages):
                masses[k, i, j]=get_mass_from_iso(iso, age, slope, mass_type=mass_type, verbose=False, remnants=remnants)

    
    if remnants:
        fname='/home/vaughan/Science/MIST_isochrones/CvD16_mass_files/CvD16_mass_file_{}_with_remnants.dat'.format(mass_type)
    else:
        fname='/home/vaughan/Science/MIST_isochrones/CvD16_mass_files/CvD16_mass_file_{}_without_remnants.dat'.format(mass_type)

    with file(fname, 'w') as outfile:
    # I'm writing a header here just for the sake of readability
    # Any line starting with "#" will be ignored by numpy.loadtxt
        outfile.write('# Array shape: {0}\n'.format(masses.shape))

        # Iterating through a ndimensional array produces slices along
        # the last axis. This is equivalent to data[i,:,:] in this case
        for data_slice in masses:

            # The formatting string indicates that I'm writing out
            # the values in left-justified columns 7 characters in width
            # with 2 decimal places.  
            np.savetxt(outfile, data_slice, fmt='%1.10f')

            # Writing out a break to indicate different slices...
            outfile.write('# New slice\n')

    print 'Saved mass text file to {}'.format(fname)





