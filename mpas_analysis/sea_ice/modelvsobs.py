import os
import os.path
import subprocess
import matplotlib.pyplot as plt
import matplotlib.colors as cols

import numpy as np
import numpy.ma as ma

import netCDF4

from ..shared.plot.plotting import plot_polar_comparison

from ..shared.io import NameList, StreamsFile
from ..shared.io.utility import buildConfigFullPath

from ..shared.generalized_reader.generalized_reader \
    import open_multifile_dataset

from ..shared.timekeeping.utility import get_simulation_start_time, \
    days_to_datetime


def seaice_modelvsobs(config, streamMap=None, variableMap=None):
    """
    Performs analysis of sea-ice properties by comparing with
    previous model results and/or observations.

    config is an instance of MpasAnalysisConfigParser containing configuration
    options.

    If present, streamMap is a dictionary of MPAS-O stream names that map to
    their mpas_analysis counterparts.

    If present, variableMap is a dictionary of MPAS-O variable names that map
    to their mpas_analysis counterparts.

    Author: Xylar Asay-Davis, Milena Veneziani
    Last Modified: 02/02/2017
    """

    # read parameters from config file
    inDirectory = config.get('input', 'baseDirectory')

    namelistFileName = config.get('input', 'seaIceNamelistFileName')
    namelist = NameList(namelistFileName, path=inDirectory)

    streamsFileName = config.get('input', 'seaIceStreamsFileName')
    streams = StreamsFile(streamsFileName, streamsdir=inDirectory)

    oceanStreamsFileName = config.get('input', 'oceanStreamsFileName')
    oceanStreams = StreamsFile(oceanStreamsFileName, streamsdir=inDirectory)

    calendar = namelist.get('config_calendar_type')
    try:
        simulationStartTime = get_simulation_start_time(streams)
    except IOError:
        # try the ocean stream instead
        simulationStartTime = get_simulation_start_time(oceanStreams)
    # get a list of timeSeriesStatsMonthly output files from the streams file,
    # reading only those that are between the start and end dates
    startDate = config.get('climatology', 'startDate')
    endDate = config.get('climatology', 'endDate')
    streamName = streams.find_stream(streamMap['timeSeriesStats'])
    fileNames = streams.readpath(streamName, startDate=startDate,
                                 endDate=endDate, calendar=calendar)
    print 'Reading files {} through {}'.format(fileNames[0], fileNames[-1])

    plotsDirectory = buildConfigFullPath(config, 'output', 'plotsSubdirectory')

    mainRunName = config.get('runs', 'mainRunName')

    mpasRemapFile = config.get('remapping', 'mpasRemapFile')
    climatologyDirectory = buildConfigFullPath(config, 'output',
                                               'climatologySubdirectory')

    startYear = config.getint('climatology', 'startYear')
    endYear = config.getint('climatology', 'endYear')

    # climatologyDirectory = "{}/{}".format(climatologyDirectory, mainRunName)
    climatologyRegriddedDirectory = "{}/mpas_regridded".format(
        climatologyDirectory)
    if not os.path.isdir(climatologyDirectory):
        print "\nClimatology directory does not exist. Create it...\n"
        os.mkdir(climatologyDirectory)
    if not os.path.isdir(climatologyRegriddedDirectory):
        print "\nRegridded directory does not exist. Create it...\n"
        os.mkdir(climatologyRegriddedDirectory)

    # Model climatology (output) filenames
    climatologyFiles = {}
    climatologyFiles['winNH'] = \
        "mpas-cice_climo.years{:04d}-{:04d}.jfm.nc".format(startYear, endYear)
    climatologyFiles['sumNH'] = \
        "mpas-cice_climo.years{:04d}-{:04d}.jas.nc".format(startYear, endYear)
    climatologyFiles['winSH'] = \
        "mpas-cice_climo.years{:04d}-{:04d}.djf.nc".format(startYear, endYear)
    climatologyFiles['sumSH'] = \
        "mpas-cice_climo.years{:04d}-{:04d}.jja.nc".format(startYear, endYear)
    climatologyFiles['on'] = \
        "mpas-cice_climo.years{:04d}-{:04d}.on.nc".format(startYear, endYear)
    climatologyFiles['fm'] = \
        "mpas-cice_climo.years{:04d}-{:04d}.fm.nc".format(startYear, endYear)

    # make a dictionary of the months in each climotology
    monthsInClim = {}
    monthsInClim['winNH'] = [1, 2, 3]
    monthsInClim['sumNH'] = [7, 8, 9]
    monthsInClim['winSH'] = [12, 1, 2]
    monthsInClim['sumSH'] = [6, 7, 8]
    monthsInClim['on'] = [10, 11]
    monthsInClim['fm'] = [2, 3]

    # Obs filenames
    obsIceConcFileNames = {}
    obsIceConcFileNames['winNH_NASATeam'] = buildConfigFullPath(
                                             config, 'seaIceObservations',
                                             'concentrationNASATeamNH_JFM')
    obsIceConcFileNames['sumNH_NASATeam'] = buildConfigFullPath(
                                             config, 'seaIceObservations',
                                             'concentrationNASATeamNH_JAS')
    obsIceConcFileNames['winSH_NASATeam'] = buildConfigFullPath(
                                             config, 'seaIceObservations',
                                             'concentrationNASATeamSH_DJF')
    obsIceConcFileNames['sumSH_NASATeam'] = buildConfigFullPath(
                                             config, 'seaIceObservations',
                                             'concentrationNASATeamSH_JJA')
    obsIceConcFileNames['winNH_Bootstrap'] = buildConfigFullPath(
                                              config, 'seaIceObservations',
                                              'concentrationBootstrapNH_JFM')
    obsIceConcFileNames['sumNH_Bootstrap'] = buildConfigFullPath(
                                              config, 'seaIceObservations',
                                              'concentrationBootstrapNH_JAS')
    obsIceConcFileNames['winSH_Bootstrap'] = buildConfigFullPath(
                                              config, 'seaIceObservations',
                                              'concentrationBootstrapSH_DJF')
    obsIceConcFileNames['sumSH_Bootstrap'] = buildConfigFullPath(
                                              config, 'seaIceObservations',
                                              'concentrationBootstrapSH_JJA')

    obsIceThickFileNames = {}
    obsIceThickFileNames['onNH'] = buildConfigFullPath(
                                    config, 'seaIceObservations',
                                    'thicknessNH_ON')
    obsIceThickFileNames['fmNH'] = buildConfigFullPath(
                                    config, 'seaIceObservations',
                                    'thicknessNH_FM')
    obsIceThickFileNames['onSH'] = buildConfigFullPath(
                                    config, 'seaIceObservations',
                                    'thicknessSH_ON')
    obsIceThickFileNames['fmSH'] = buildConfigFullPath(
                                    config, 'seaIceObservations',
                                    'thicknessSH_FM')

    # Checks on directory/files existence:
    for climName in obsIceConcFileNames:
        obsFileNames = obsIceConcFileNames[climName]
        if not os.path.isfile(obsFileNames):
            raise SystemExit("Obs file {} not found. Exiting...".format(
                obsFileNames))
    for climName in obsIceThickFileNames:
        obsFileNames = obsIceThickFileNames[climName]
        if not os.path.isfile(obsFileNames):
            raise SystemExit("Obs file {} not found. Exiting...".format(
                obsFileNames))

    # Load data
    print "  Load sea-ice data..."
    ds = open_multifile_dataset(fileNames=fileNames,
                                calendar=calendar,
                                simulationStartTime=simulationStartTime,
                                timeVariableName='Time',
                                variableList=['iceAreaCell',
                                              'iceVolumeCell'],
                                variableMap=variableMap,
                                startDate=startDate,
                                endDate=endDate)

    # Compute climatologies (first motnhly and then seasonally)
    print "  Compute seasonal climatologies..."

    months = [date.month for date in days_to_datetime(ds.Time,
                                                      calendar=calendar)]

    ds.coords['month'] = ('Time', months)
    monthlyClimatology = ds.groupby('month').mean('Time')

    daysInMonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    monthLetters = ['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D']

    climatologies = {}
    for climName in monthsInClim:
        months = monthsInClim[climName]
        month = months[0]
        days = daysInMonth[month-1]
        climatology = days*monthlyClimatology.sel(month=month)
        totalDays = days
        for month in months[1:]:
            days = daysInMonth[month-1]
            climatology += days*monthlyClimatology.sel(month=month)
            totalDays += days
        climatology /= totalDays

        climatologies[climName] = climatology

    print "  Regrid fields to regular grid..."
    for climName in climatologies:
        # Save to netcdf files
        outFileName = "{}/{}".format(climatologyDirectory,
                                     climatologyFiles[climName])
        climatologies[climName].to_netcdf(outFileName)
        args = ["ncremap", "-P", "mpas", "-i", outFileName,
                "-m", mpasRemapFile, "-O", climatologyRegriddedDirectory]
        try:
            subprocess.check_call(args)
        except subprocess.CalledProcessError, e:
            print 'Error with call ', ' '.join(args)
            print e
            raise e

    print "  Make ice concentration plots..."
    subtitle = "Ice concentration"

    # interate over observations of sea-ice concentration
    first = True
    for season in ['Winter', 'Summer']:
        for hemisphere in ['NH', 'SH']:
            climName = '{}{}'.format(season[0:3].lower(), hemisphere)

            if hemisphere == 'NH':
                plotProjection = 'npstere'
            else:
                plotProjection = 'spstere'

            resultConcContourValues = config.getExpression(
                'regriddedSeaIceConcThick',
                'resultConc{}ContourValues'.format(season))
            resultColormap = plt.get_cmap(config.get(
                'regriddedSeaIceConcThick', 'resultColormap'))
            resultColormapIndices = config.getExpression(
                'regriddedSeaIceConcThick', 'resultColormapIndices')
            resultColormap = cols.ListedColormap(
                resultColormap(resultColormapIndices), "resultColormap")

            differenceConcContourValues = config.getExpression(
                'regriddedSeaIceConcThick',
                'differenceConc{}ContourValues'.format(season))
            differenceColormap = plt.get_cmap(config.get(
                'regriddedSeaIceConcThick', 'differenceColormap'))
            differenceColormapIndices = config.getExpression(
                'regriddedSeaIceConcThick', 'differenceColormapIndices')
            differenceColormap = cols.ListedColormap(
                differenceColormap(differenceColormapIndices),
                "differenceColormap")

            referenceLongitude = config.getfloat(
                'regriddedSeaIceConcThick',
                'referenceLongitude{}'.format(hemisphere))
            minimumLatitude = config.getfloat(
                'regriddedSeaIceConcThick',
                'minimumLatitude{}'.format(hemisphere))

            # Load in sea-ice data
            #  Model...
            # ice concentrations
            fileName = "{}/{}".format(climatologyRegriddedDirectory,
                                      climatologyFiles[climName])
            ncFile = netCDF4.Dataset(fileName, mode='r')
            iceConcentration = ncFile.variables["iceAreaCell"][:]
            if(first):
                lons = ncFile.variables["lon"][:]
                lats = ncFile.variables["lat"][:]
                print "Min lon: ", np.amin(lons), "Max lon: ", np.amax(lons)
                print "Min lat: ", np.amin(lats), "Max lat: ", np.amax(lats)
                Lons, Lats = np.meshgrid(lons, lats)
                first = False
            ncFile.close()

            #  ...and observations
            # ice concentrations from NASATeam (or Bootstrap) algorithm
            for obsName in ['NASATeam', 'Bootstrap']:

                fileName = obsIceConcFileNames[
                    '{}_{}'.format(climName, obsName)]
                ncFile = netCDF4.Dataset(fileName, mode='r')
                obsIceConcentration = ncFile.variables["AICE"][:]
                ncFile.close()

                difference = iceConcentration - obsIceConcentration

                monthsName = []
                for month in monthsInClim[climName]:
                    monthsName.append(monthLetters[month-1])
                monthsName = ''.join(monthsName)

                title = "{} ({}, years {:04d}-{:04d})".format(
                    subtitle, monthsName, startYear, endYear)
                fileout = "{}/iceconc{}{}_{}_{}_years{:04d}-{:04d}.png".format(
                    plotsDirectory, obsName, hemisphere, mainRunName,
                    monthsName, startYear, endYear)
                plot_polar_comparison(
                    config,
                    Lons,
                    Lats,
                    iceConcentration,
                    obsIceConcentration,
                    difference,
                    resultColormap,
                    resultConcContourValues,
                    differenceColormap,
                    differenceConcContourValues,
                    title=title,
                    fileout=fileout,
                    plotProjection=plotProjection,
                    latmin=minimumLatitude,
                    lon0=referenceLongitude,
                    modelTitle=mainRunName,
                    obsTitle="Observations (SSM/I {})".format(obsName),
                    diffTitle="Model-Observations",
                    cbarlabel="fraction")

    print "  Make ice thickness plots..."
    # Plot Northern Hemisphere FM sea-ice thickness
    subtitle = "Ice thickness"
    # interate over observations of sea-ice thickness
    for climName in ['fm', 'on']:

        # Load in sea-ice data
        #  Model...
        # ice concentrations
        fileName = "{}/{}".format(climatologyRegriddedDirectory,
                                  climatologyFiles[climName])
        ncFile = netCDF4.Dataset(fileName, mode='r')
        iceThickness = ncFile.variables["iceVolumeCell"][:]
        ncFile.close()

        monthsName = []
        for month in monthsInClim[climName]:
            monthsName.append(monthLetters[month-1])
        monthsName = ''.join(monthsName)

        for hemisphere in ['NH', 'SH']:
            #  ...and observations
            # ice concentrations from NASATeam (or Bootstrap) algorithm

            resultThickContourValues = config.getExpression(
                'regriddedSeaIceConcThick',
                'resultThick{}ContourValues'.format(hemisphere))
            resultColormap = plt.get_cmap(config.get(
                'regriddedSeaIceConcThick', 'resultColormap'))
            resultColormapIndices = config.getExpression(
                'regriddedSeaIceConcThick', 'resultColormapIndices')
            resultColormap = cols.ListedColormap(
                resultColormap(resultColormapIndices), "resultColormap")

            differenceThickContourValues = config.getExpression(
                'regriddedSeaIceConcThick',
                'differenceThick{}ContourValues'.format(hemisphere))
            differenceColormap = plt.get_cmap(config.get(
                'regriddedSeaIceConcThick', 'differenceColormap'))
            differenceColormapIndices = config.getExpression(
                'regriddedSeaIceConcThick', 'differenceColormapIndices')
            differenceColormap = cols.ListedColormap(
                differenceColormap(differenceColormapIndices),
                "differenceColormap")

            referenceLongitude = config.getfloat(
                'regriddedSeaIceConcThick',
                'referenceLongitude{}'.format(hemisphere))
            minimumLatitude = config.getfloat(
                'regriddedSeaIceConcThick',
                'minimumLatitude{}'.format(hemisphere))

            fileName = obsIceThickFileNames['{}{}'.format(climName,
                                                          hemisphere)]
            ncFile = netCDF4.Dataset(fileName, mode='r')
            obsIceThickness = ncFile.variables["HI"][:]
            ncFile.close()
            # Mask thickness fields
            iceThickness[iceThickness == 0] = ma.masked
            obsIceThickness = ma.masked_values(obsIceThickness, 0)
            if hemisphere == 'NH':
                # Obs thickness should be nan above 86 (ICESat data)
                obsIceThickness[Lats > 86] = ma.masked
                plotProjection = 'npstere'
            else:
                plotProjection = 'spstere'

            difference = iceThickness - obsIceThickness

            title = "{} ({}, years {:04d}-{:04d})".format(subtitle, monthsName,
                                                          startYear, endYear)
            fileout = "{}/icethick{}_{}_{}_years{:04d}-{:04d}.png".format(
                plotsDirectory, hemisphere, mainRunName, monthsName, startYear,
                endYear)
            plot_polar_comparison(
                config,
                Lons,
                Lats,
                iceThickness,
                obsIceThickness,
                difference,
                resultColormap,
                resultThickContourValues,
                differenceColormap,
                differenceThickContourValues,
                title=title,
                fileout=fileout,
                plotProjection=plotProjection,
                latmin=minimumLatitude,
                lon0=referenceLongitude,
                modelTitle=mainRunName,
                obsTitle="Observations (ICESat)",
                diffTitle="Model-Observations",
                cbarlabel="m")
