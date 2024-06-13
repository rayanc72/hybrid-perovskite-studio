#!/usr/bin/env python

import numpy as np
from os.path import join, isfile
from os import listdir
import sys
import streamlit as st

class Input(object):

    def __init__(self, latvec=[], species_id={}, k_path=[], band_sampling=[]):
        self.latvec = latvec
        self.species_id = species_id
        self.k_path = k_path
        self.band_sampling = band_sampling

    def read_geometry(self):
        count = 1
        with open("geometry.in", 'r') as fin:
            data = fin.readlines()
        for i in range(len(data)):
            item = data[i].split()
            if (len(item) == 0) or (item[0].startswith("#")):
                continue
            elif (item[0] == "lattice_vector"):
                self.latvec.append([float(i) for i in item[1:4]])
            elif (item[0] == "atom") or (item[0] == "atom_frac"):
                try:
                    self.species_id[item[-1]].append(count)
                except KeyError:
                    self.species_id[item[-1]] = []
                    self.species_id[item[-1]].append(count)
                finally:
                    count += 1

    def read_control(self):
        with open("control.in", 'r') as fin:
            data = fin.readlines()
        for i in range(len(data)):
            item = data[i].split()
            if (len(item) == 0) or (item[0].startswith("#")):
                continue
            elif (item[0] == "output"):
                if (item[1].startswith("band")):
                    self.k_path.append([float(j) for j in item[2:8]])
                    self.band_sampling.append(int(item[8]))

    def get_volume(self):
        volume = np.dot(self.latvec[0],
                        np.cross(self.latvec[1], self.latvec[2]))
        return volume

    def get_rlatvec(self):
        volume = self.get_volume()
        rlatvec = []
        rlatvec.append((2 * np.pi * np.cross(self.latvec[1], self.latvec[2]) /
                        volume).tolist())
        rlatvec.append((2 * np.pi * np.cross(self.latvec[2], self.latvec[0]) /
                        volume).tolist())
        rlatvec.append((2 * np.pi * np.cross(self.latvec[0], self.latvec[1]) /
                        volume).tolist())
        print("rlatvec")
        print(rlatvec)
        return rlatvec

    def band_x_val(self):
        r_latvec = self.get_rlatvec()
        band_len = []
        for i in range(len(self.k_path)):
            k_vec = []
            for j in range(3):
                k_vec.append(self.k_path[i][j + 3] - self.k_path[i][j])
            temp = np.sqrt(sum([k * k for k in list(np.dot(k_vec, r_latvec))]))
            step = temp / (self.band_sampling[i] - 1)
            xval = []
            xvals = []
            for k in range(self.band_sampling[i]):
                xval.append(self.k_path[i] * step)
            xvals.append(xval)
            band_len.append(temp)
        band_len_tot = []
        for i in range(len(band_len)):
            if (i == 0):
                band_len_tot.append(0)
            else:
                band_len_tot.append(sum(band_len[:i]))
        print(band_len_tot)
        return band_len_tot

    def print_atoms(self):
        print(self.species_id)
        print(self.latvec)
        print(self.band_sampling)
        print(self.k_path)


class Band(object):

    def __init__(self, eigenvalues={}, sampling=0,
                 coordinate=[]):
        self.eigenvalues = eigenvalues
        self.sampling = sampling
        self.coordinate = coordinate

    def get_band(self, data):
        # with open(filename, 'r') as fin:
        #     data = fin.readlines()
        self.sampling = len(data)
        for grid in range(self.sampling):
            item = data[grid].split()
            self.coordinate.append([float(k) for k in item[1:4]])
            for i in range(1, int((len(item) - 4) / 2 + 1)):
                try:
                    self.eigenvalues[i].append(float(item[2 * i + 3]))
                except KeyError:
                    self.eigenvalues[i] = [float(item[2 * i + 3])]

    def get_band(self, data):
        # Convert bytes data to string if necessary
        if isinstance(data, bytes):
            data = data.decode('utf-8')

        # Split the data into lines
        data = data.splitlines()

        self.sampling = len(data)
        self.coordinate = []  # Ensure coordinate is initialized
        self.eigenvalues = {}  # Ensure eigenvalues is initialized

        for grid in range(self.sampling):
            item = data[grid].split()
            self.coordinate.append([float(k) for k in item[1:4]])
            for i in range(1, int((len(item) - 4) / 2 + 1)):
                eigenvalue_index = 2 * i + 3
                if eigenvalue_index < len(item):
                    try:
                        self.eigenvalues[i].append(float(item[eigenvalue_index]))
                    except KeyError:
                        self.eigenvalues[i] = [float(item[eigenvalue_index])]

    def print_VBM(self, line=0.00):
        results=[]
        for state in self.eigenvalues:
            if(max(self.eigenvalues[state + 1]) > line):
                break
        max_energy = max(self.eigenvalues[state])
        VBM_list = [x for x in range(len(self.eigenvalues[state]))
                    if (self.eigenvalues[state][x] == max_energy)]
        for i in range(len(VBM_list)):
            results.append({
                "State": state,
                "Coordinate": self.coordinate[VBM_list[i]],
                "Energy": max_energy
            })

        return max(results, key=lambda x: x["Energy"]) if results else None
    #         return("State: " + str(state) + "Coordinate: " + str(self.coordinate[VBM_list[i]]) + "  " +
    #               "Energy: " + str(max_energy) + " eV")
    #

    def print_CBM(self, line=0.00):
        results=[]
        for state in self.eigenvalues:
            if(max(self.eigenvalues[state + 1]) > line):
                break
        state = state + 1
        min_energy = min(self.eigenvalues[state])
        CBM_list = [x for x in range(len(self.eigenvalues[state]))
                    if (self.eigenvalues[state][x] == min_energy)]
        # print("CBM energy: " + str(min_energy) + " eV")
        # print("Current state: " + str(state))
        for i in range(len(CBM_list)):
            results.append({
                "State": state,
                "Coordinate": self.coordinate[CBM_list[i]],
                "Energy": min_energy
            })
            # return("Coordinate: " + str(self.coordinate[CBM_list[i]]) + "  " +
            #       "Energy: " + str(min_energy) + " eV")
        return min(results, key=lambda x: x["Energy"]) if results else None

    def find_VBM_state(self, line=0.01):
        for state in self.eigenvalues:
            if(max(self.eigenvalues[state + 1]) > line):
                break
        return state

    def find_VBM_energy(self, line=0.01):
        VBM_state = self.find_VBM_state(line)
        print(" ")
        print(VBM_state)
        return(max(self.eigenvalues[VBM_state]), VBM_state)


if(__name__ == "__main__"):
    control = Input()
    if (len(sys.argv) > 1):
        myLine = float(sys.argv[1])
    else:
        myLine = 0
    current_band = Band()
    onlyfiles = [f for f in listdir('.') if isfile(join('.', f))]
    bandfiles = [f for f in onlyfiles
                 if (f.startswith('band')) and ('.out' in f)
                 and ('mlk' not in f)]
    bandfiles.sort()
    for f in bandfiles:
        st.write(f)
        current_band.get_band(f)
    print(len(current_band.coordinate))
    current_band.print_VBM(line=myLine)
    current_band.print_CBM(line=myLine)
# current_band.find_VBM_state)

