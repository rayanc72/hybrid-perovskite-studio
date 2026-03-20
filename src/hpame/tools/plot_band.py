#!/usr/bin/env python
# To run this script, ./band_original.py energy_shift filename

import sys
import matplotlib.pyplot as plt
import matplotlib
import math
from os import listdir
from os.path import isfile, join
import numpy as np
from numpy import pi

matplotlib.rcParams.update({'font.size': 20})
matplotlib.rcParams['axes.linewidth'] = 2
matplotlib.rcParams['font.family'] = 'serif'
matplotlib.rcParams['font.serif'] = ['Times New Roman']
fig = plt.gcf()
fig.set_size_inches(10, 6)
linewidth = 1
black_bands = 1
special_line = 3
inorghomo = []
orghomo = []
# orghomo.append(int(sys.argv[4]))
orglumo = []
inorglumo = []


def process_geometry_file(filename='geometry.in'):
    latvec = []
    rlatvec = []

    with open(filename) as f:
        for line in f:
            words = line.strip().split()
            if len(words) == 0:
                continue
            if words[0] == "lattice_vector":
                latvec.append([float(i) for i in words[1:4]])

    print("Lattice vectors:")
    for j in range(3):
        print(latvec[j])
    print()

    #Calculate reciprocal lattice vectors
    volume = (np.dot(latvec[0],np.cross(latvec[1],latvec[2])))
    rlatvec.append(2*pi*np.cross(latvec[1],latvec[2])/volume)
    rlatvec.append(2*pi*np.cross(latvec[2],latvec[0])/volume)
    rlatvec.append(2*pi*np.cross(latvec[0],latvec[1])/volume)

    print("Reciprocal lattice vectors:")
    for j in range(3):
        print(rlatvec[j])
    print()

    return rlatvec

def process_control_file(filename='control.in'):
    k_label = []
    kpoint = []
    rlatvec = process_geometry_file(filename='geometry.in')

    with open(filename) as f:
        for line in f:
            if line.strip().startswith('output band'):
                words = line.strip().split()
                kpoint.append([float(i) for i in words[2:8]])
                n_sample = int(words[-3])
                k_label.append(words[-2:])

    print('K path')
    print(kpoint)
    band_len = []
    print(k_label)

    k_label_reduce = []
    for k_pair in k_label:
        for i in range(len(k_pair)):
            k = k_pair[i]
            if len(k_label_reduce) == 0:
                k_label_reduce.append(k)
            elif i == 0 and k != k_label_reduce[-1]:
                k_label_reduce[-1] = k_label_reduce[-1] + "|" + k
            elif i == 0 and k == k_label_reduce[-1]:
                continue
            else:
                k_label_reduce.append(k)

    print(k_label_reduce)

    xvals = []
    for i in kpoint:
        kvec = []
        for j in range(3):
            kvec.append(i[j + 3] - i[j])
        temp = math.sqrt(sum([k * k for k in list(np.dot(kvec, rlatvec))]))
        step = temp / (n_sample - 1)
        xval = []
        for i in range(n_sample):
            xval.append(i * step)
        xvals.append(xval)
        band_len.append(temp)

    band_len_tot = []
    for i in range(len(band_len)):
        if i == 0:
            band_len_tot.append(0)
        else:
            band_len_tot.append(sum(band_len[:i]))

    for i in range(len(xvals)):
        xvals[i] = [j + band_len_tot[i] for j in xvals[i]]

    print('x values')
    band_len_tot.append(xvals[-1][-1])

    return k_label, kpoint, band_len, k_label_reduce, xvals, band_len_tot

def parse_output_files(path='.', energyshift=None):
    onlyfiles = [f for f in listdir(path) if isfile(join(path, f))]
    bandfiles = [f for f in onlyfiles if f.startswith('band') and '.out' in f and len(f) == 12]
    bandfiles = sorted(bandfiles, key=lambda x: int(x[4:-4]))

    bands_all_files = []
    for file_id in range(len(bandfiles)):
        file = bandfiles[file_id]
        print(file)
        energys = []

        with open(file) as f:
            for line in f:
                words = line.strip().split()
                energy = []
                occ_ene = words[4:]
                for i in range(0, len(occ_ene), 2):
                    energy.append(float(occ_ene[i+1]) - energyshift)
                energys.append(energy)

        bands = []
        for i in range(len(energy)):
            band = []
            for j in range(len(energys)):
                band.append(energys[j][i])
            bands.append(band)
        bands_all_files.append(bands)

    return bands_all_files

def plot_bands(
    bands_all_files,
    xvals=None,
    band_len_tot=None,
    k_label_reduce=None,
    ymin=None,
    ymax=None,
    filename=None,
    orghomo=None,
    inorghomo=None,
    orglumo=None,
    inorglumo=None,
    special_line=None,
    solid=None,
    black_bands=None,
    color="k",
):
    for file_id, bands in enumerate(bands_all_files):
        for band_id, band in enumerate(bands):
            if band_id in orghomo:
                plt.plot(xvals[file_id], band, color='g', lw=special_line)
            elif band_id in inorghomo:
                plt.plot(xvals[file_id], band, color='r', lw=special_line)
            elif band_id in orglumo:
                if file_id in solid:
                    plt.plot(xvals[file_id], band, 'b', lw=special_line)
                else:
                    plt.plot(xvals[file_id], band, 'b--', lw=special_line)
            elif band_id in inorglumo:
                if file_id in solid:
                    plt.plot(xvals[file_id], band, 'r', lw=special_line)
                else:
                    plt.plot(xvals[file_id], band, 'r:', lw=special_line)
            else:
                plt.plot(xvals[file_id], band, color=color, lw=black_bands)

    for kpoint_x in band_len_tot[1:]:
        plt.axvline(kpoint_x, color='k', linestyle = '--', lw=linewidth).set_dashes([5,5])
    plt.axhline(0, color='k', linestyle = '--', lw=linewidth).set_dashes([5,5])

    plt.xticks([])
    plt.xticks(band_len_tot, k_label_reduce, size=18)
    plt.ylabel('Energy(ev)')
    plt.axis([0, max([abs(i) for i in xvals[-1]]), ymin, ymax])
    plt.savefig(filename, dpi = 300, bbox_inches='tight')

def main(argv=None):
    argv = sys.argv if argv is None else argv
    energyshift = float(argv[1])
    ymin = float(argv[2])
    ymax = float(argv[3])
    filename = argv[4]
    color = argv[5]

    k_label, kpoint, band_len, k_label_reduce, xvals, band_len_tot = process_control_file(filename='control.in')
    bands_all_files = parse_output_files(energyshift=energyshift)
    plot_bands(
        bands_all_files,
        xvals=xvals,
        band_len_tot=band_len_tot,
        k_label_reduce=k_label_reduce,
        ymin=ymin,
        ymax=ymax,
        filename=filename,
        orghomo=orghomo,
        inorghomo=inorghomo,
        orglumo=orglumo,
        inorglumo=inorglumo,
        special_line=special_line,
        black_bands=black_bands,
        color=color,
    )


if __name__ == "__main__":
    main()
