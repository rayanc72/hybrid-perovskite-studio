
from structure_manager import *
import plotly.express as px
from molecule_builder import *
from electronic_property import *
from contextlib import redirect_stdout
from MD_analysis import *
import streamlit as st
import subprocess
import os
import shutil
from pathlib import Path
import requests
from PIL import Image
from streamlit_lottie import st_lottie
from streamlit_ketcher import st_ketcher


# structure_content = None

st.set_page_config(page_title="hPAME", layout="wide")

st.title("hybrid :red[Perovskite Analysis and Modelling Engine]")

st.divider()
st.latex(r'''\rm Download\; a\;  structure\;  file\;  from\;  HybriD^3:''')
with st.expander("Expand for options"):

    col1, col2, col3 = st.columns([3,0.5,3])
    with col2:
        # st.image(image_db, use_column_width=True)
        st_lottie("https://lottie.host/90f085a3-e3b9-440d-83ab-ddec87f2b5d6/e904WGCrzS.json")



    conn = st.connection("hybrid3_1410", type="sql", autocommit=True)
    systems = conn.query("select * from materials_system")

    # Taking user input for the search string, system ID, and dataset ID
    user_input = st.text_input("Enter search string (e.g., BA2PbI4):")
    system_id = st.text_input("Enter system ID:")
    dataset_id = st.text_input("Enter dataset ID:")

    structure_file_path = None

    # Handling the logic based on the provided input
    if dataset_id:  # If dataset ID is provided, it takes precedence
        try:
            zip_url = f"https://materials.hybrid3.duke.edu/materials/datasets/{dataset_id}/files"
            response = requests.get(zip_url, stream=True)
            response.raise_for_status()

            # Writing the zip file to a temporary location and allowing the user to download
            zip_data = response.content
            file_content, file_extension = extract_structure_file(zip_data)
            if file_content:
                # Use st.download_button to allow the user to download the file
                st.download_button(
                    label=f"Download {dataset_id}{file_extension}",
                    data=file_content,
                    file_name=f"{dataset_id}{file_extension}",
                    mime=f"text/{file_extension[1:]}"  # assuming mime type to be text/in or text/cif
                )

            # if st.button("Load structure"):
            #     structure_file_path = extract_structure_file_path(zip_data)
            #     if not structure_file_path:
            #         st.write("No .in or .cif file found in the zip archive.")

        except requests.exceptions.RequestException as err:
            st.write(f"Error fetching dataset: {err}")

    # Handling the logic based on the provided input
    elif system_id:  # Next priority is system ID
        try:
            matched_df = systems[systems['id'] == int(system_id)][['id', 'compound_name', 'formula']]
            if not matched_df.empty:
                st.write(f"Information for ID '{system_id}':")
                st.dataframe(matched_df, hide_index=True, use_container_width=True)
                dataset_results = fetch_materials_datasets(conn, int(system_id))

                # Displaying only 'dataset_id' and 'space_group' columns
                st.write("Associated structure datasets:")
                st.dataframe(dataset_results[['id', 'space_group']], hide_index=True, use_container_width=True)
            else:
                st.write(f"No results found for ID '{system_id}'.")
        except ValueError:
            st.write("Please enter a valid ID.")
    elif user_input:  # Only check for search string if ID is not provided
        matched_ids = search_database(systems, user_input)
        matched_df = systems[systems['id'].isin(matched_ids)][['id', 'compound_name', 'formula']]
        st.write(f"Information for matched IDs with '{user_input}':")
        st.dataframe(matched_df, hide_index=True, use_container_width=True)




# st.divider()

st.subheader("Upload a structure file (:blue[aims geometry] or :blue[CIF]) to get started: ")


file_buffer = st.file_uploader("Something", type=[".in", ".cif", ".next_step"], label_visibility='hidden')

atoms = None
molecules = None
if 'atoms' not in st.session_state:
    st.session_state.atoms = None

if 'file_name' not in st.session_state:
    st.session_state.file_name = None


if file_buffer is not None:
    file_name = file_buffer.name
    file_format = get_file_format(file_name)

    if file_buffer is not None:
        file_name = file_buffer.name
        file_format = get_file_format(file_name)

        if file_buffer is not None:
            if 'atoms' not in st.session_state or st.session_state.file_name != file_name:
                try:
                    file_format = get_file_format(file_buffer.name)
                    atoms, molecules, modified_symbols = initialize_structure(file_buffer, file_format=file_format,
                                                                              file_name=file_buffer.name, exceptions=[("F", "I")])
                    st.session_state.atoms = copy.deepcopy(atoms)
                    st.session_state.molecules = molecules
                    st.session_state.modified_symbols = modified_symbols
                    st.session_state.file_name = file_name
                except Exception as e:
                    st.error(f"Error loading the file: {str(e)}")
                    # raise StopExecution

            output_suffix = ""
            with st.expander("Get labelled atoms"):
                create_labelled_download_file(st.session_state.atoms, file_name, output_suffix)

            space_group = print_space_group(st.session_state.atoms)
            with st.expander("See symmetry information"):
                st.markdown(f"```\n{space_group}\n```")

            # extended_space_group_info = extended_symmetry_info(st.session_state.atoms)
            # with st.expander("See extended symmetry information"):
            #     st.markdown(f"```\n{extended_space_group_info}\n```")


            molecule_list = []
            for i, molecule in enumerate(st.session_state.molecules, 1):
                molecule_labels = [st.session_state.modified_symbols[mol_atom] for mol_atom in molecule]
                molecule_list.append(f"Molecule {i}: {', '.join(molecule_labels)}")

            molecule_list_formatted = "\n".join(molecule_list)

            with st.expander("See detected molecules"):
                st.markdown(f"```\n{molecule_list_formatted}\n```")

            with st.expander("Get geometry.in"):
                create_aims_download_file(st.session_state.atoms, file_name, output_suffix)

            with st.expander("See structure"):
                atoms_to_speck(st.session_state.atoms, "initialization")

            # except Exception as e:
            #     st.error(f"Error: {e}")


with st.sidebar:
    st.sidebar.header("Structure Analysis")



    #Section 1 - general structure analysis
    symmetry_option = st.sidebar.checkbox("Symmetrize structure", value=False)
    com_option = st.sidebar.checkbox("Find center of mass", value=False)
    dm_option = st.sidebar.checkbox("Calculate dipole moment", value=False)
    distance_option = st.sidebar.checkbox("Calculate atomic distances", value=False)
    distortion_option = st.sidebar.checkbox("Calculate octahedral distortions", value=False)
    deviation_calculation_option = st.sidebar.checkbox("Calculate percentage deviation", value=False)

    st.divider()

    st.sidebar.header("Structure Transformations")
    #Section 2 - operations
    rotate_option = st.sidebar.checkbox("Rotation", value=False)
    # rotation_all_same_options = st.sidebar.checkbox("Rotate Multiple Molecules", value=False)
    # rotate_some_atoms_option = st.sidebar.checkbox("Rotate Part of Molecules", value=False)
    # interp_rotate_option = st.sidebar.checkbox("Interpolation by Rotation", value=False)
    # rotate_by_dm_option = st.sidebar.checkbox("Rotate dipole moment", value=False)
    reflect_option = st.sidebar.checkbox("Reflection", value=False)
    translation_option = st.sidebar.checkbox("Translation", value=False)
    delete_option = st.sidebar.checkbox("Deletion", value=False)
    create_cent_option = st.sidebar.checkbox("Create centrosymmetric structure", value=False)
    interpolate_option = st.sidebar.checkbox("Standard interpolation", value=False)
    trans_rotate_option = st.sidebar.checkbox("Interpolation by Translation + Rotation", value=False)

    # visulization_option = st.sidebar.checkbox("Visualize Structures", value=False)
    # exp_option = st.sidebar.checkbox("Experimental", value=False)

    st.divider()

    st.sidebar.header("Electronic Analysis")
    #Section 3 - data analysis
    plot_polarization_option = st.sidebar.checkbox("Plot polarization", value=False)
    plot_pdos_option = st.sidebar.checkbox("Plot partial density of states (PDOS)", value=False)
    plot_bs_option = st.sidebar.checkbox("Plot bandstructure", value=False)
    plot_spin_option = st.sidebar.checkbox("Plot spin texture", value=False)
    # plot_mul_bs_option = st.sidebar.checkbox("Plot Mulliken Bandstructure", value=False)

    st.divider()

    st.sidebar.header("Dynamics Analysis")
    MD_option = st.sidebar.checkbox("Analyze AIMS MD output", value=False)
    MDanalysis_option = st.sidebar.checkbox("Distance analysis with MDA", value=False)

    # st.divider()
    #
    # st.sidebar.header("Access Databases")
    # local_database = st.sidebar.checkbox("Access HybriD3 Database (local)", value=False)

# sketch_option = st.sidebar.checkbox("Get SMILES", value=False)

# perpendicular_axis_option = st.sidebar.checkbox("Get perpendicular axis", value=False)


# if 'use_custom_axis' not in st.session_state:
#     st.session_state.use_custom_axis = True


if st.session_state.atoms is not None:

    modified_atoms = st.session_state.atoms.copy()
    # st.session_state.modified_atoms = modified_atoms
    molecules = st.session_state.molecules.copy()


    if rotate_option:
        st.header("Rotation")

        rotate_type = st.selectbox("Select Rotation Type", (
        "Rotate Individual Molecules", "Rotate Multiple Molecules", "Interpolate by Rotation", "Rotate Part of Molecules", "Rotate by Dipole Moment"))


        if rotate_type == "Rotate Individual Molecules":



            # Gather user inputs for rotation using Streamlit widgets
            molecule_indices = st.multiselect("Select molecule indices", options=range(1, len(molecules) + 1))

            if molecule_indices is not None:

                if "rotation_parameters" not in st.session_state:
                    st.session_state.rotation_parameters = [None] * len(molecules)

                for i in molecule_indices:
                    st.subheader(f"Molecule {i}")

                    with st.form(key=f"molecule_{i}_form"):

                        axis_input = st.text_input("Enter crystal direction as h, k, l separated by spaces")

                        # Add the centroid option selection
                        angle = st.number_input("Enter rotation angle in degrees", step=1.0)

                        if st.form_submit_button(f"Set Parameters for Molecule {i}"):
                            hkl = np.array([int(val) for val in axis_input.split()])
                            lattice_vectors = modified_atoms.get_cell()
                            axis = np.dot(hkl, lattice_vectors)
                            axis /= np.linalg.norm(axis)

                            st.session_state.rotation_parameters[i - 1] = (axis, angle)


                if st.button("Apply Multiple Rotations"):
                    chosen_molecules = [molecules[i - 1] for i in molecule_indices]
                    chosen_rotation_parameters = [st.session_state.rotation_parameters[i - 1] for i in molecule_indices]

                    for molecule, (axis, angle) in zip(chosen_molecules, chosen_rotation_parameters):
                        modified_atoms = rotate_molecules_v2(modified_atoms, molecule, axis, angle)

                    # Save modified atoms to temporary files
                    output_suffix = "_rotated"
                    file_name = os.path.splitext(st.session_state.file_name)[0]

                    create_aims_download_file(modified_atoms, file_name, output_suffix)

                    create_labelled_download_file(modified_atoms, file_name, output_suffix)

        if rotate_type == "Rotate Multiple Molecules":
            st.header("Rotate Molecules (Same operation for all chosen molecules)")
            # Gather user inputs for rotation using Streamlit widgets
            molecule_indices = st.multiselect("Select molecule indices", options=range(1, len(molecules) + 1))


            axis_option = st.selectbox("Choose axis option", options=["Cartesian axis", "Crystal direction", "Custom axis"])
            axis_input = None
            if axis_option == "Cartesian axis":
                axis_input = st.selectbox("Select rotation axis", options=["x", "y", "z"])
            elif axis_option == "Crystal direction":
                axis_input = st.text_input("Enter crystal direction as h, k, l separated by spaces")
            elif axis_option == "Custom axis":
                axis_input = st.text_input("Enter custom axis as x, y, z separated by spaces")

            # Add the centroid option selection
            centroid_option = st.selectbox("Choose centroid option", options=[("1: Center of mass", 1),
                                                                              ("2: Custom", 2),
                                                                              ("3: Center of unit cell", 3)],
                                           format_func=lambda o: o[0])[1]

            custom_centroid = None
            if centroid_option == 2:
                custom_centroid = st.text_input("Enter custom centroid as x, y, z separated by spaces")
            angle = st.number_input("Enter rotation angle in degrees", step=1.0)

            if st.button("Apply Rotation") and axis_input:
                if axis_option == "Cartesian axis":
                    axis_dict = {'x': [1, 0, 0], 'y': [0, 1, 0], 'z': [0, 0, 1]}
                    axis = axis_dict[axis_input]
                elif axis_option == "Crystal direction":
                    hkl = np.array([int(val) for val in axis_input.split()])
                    lattice_vectors = modified_atoms.get_cell()
                    axis = np.dot(hkl, lattice_vectors)
                    axis /= np.linalg.norm(axis)
                elif axis_option == "Custom axis":
                    axis = np.array([float(val) for val in axis_input.split()])

                # Pass custom centroid if centroid_option is 2, otherwise pass None
                custom_centroid = np.array(
                    [float(val) for val in custom_centroid.split()]) if centroid_option == 2 else None

                modified_atoms = rotate_molecules_v3(modified_atoms, molecules, molecule_indices, axis, angle,
                                                  centroid_option, custom_centroid)


                # Save modified atoms to temporary files
                output_suffix = "_rotated"
                file_name = os.path.splitext(st.session_state.file_name)[0]


                create_aims_download_file(modified_atoms, file_name, output_suffix)

                create_labelled_download_file(modified_atoms, file_name, output_suffix)

            with st.expander("See structure"):
                with st.form(key="structure_viz"):
                    if st.form_submit_button("Update Strcuture"):
                        atoms_to_speck(modified_atoms, "rotation")
                    else:
                        atoms_to_speck(modified_atoms, "rotation")

        if rotate_type == "Interpolate by Rotation":
            st.header("Create a Series of Structures")

            # Gather user inputs for rotation using Streamlit widgets
            molecule_indices = st.multiselect("Select molecule indices", options=range(1, len(molecules) + 1))

            if molecule_indices is not None:

                if "rotation_parameters" not in st.session_state:
                    st.session_state.rotation_parameters = [None] * len(molecules)

                angle_range = st.slider("Enter rotation angle range (min, max) in degrees", min_value=0, max_value=360,
                                        value=(0, 180))
                num_structures = st.number_input("Enter the number of structures to generate", min_value=1, value=1, step=1)

                for i in molecule_indices:
                    st.subheader(f"Molecule {i}")

                    with st.form(key=f"molecule_{i}_form"):

                        axis_input = st.text_input("Enter crystal direction as h, k, l separated by spaces")

                        if st.form_submit_button(f"Set Parameters for Molecule {i}"):
                            hkl = np.array([int(val) for val in axis_input.split()])
                            lattice_vectors = modified_atoms.get_cell()
                            axis = np.dot(hkl, lattice_vectors)
                            axis /= np.linalg.norm(axis)

                            st.session_state.rotation_parameters[i - 1] = axis

                if st.button("Apply Multiple Rotations"):
                    chosen_molecules = [molecules[i - 1] for i in molecule_indices]
                    chosen_rotation_axes = [st.session_state.rotation_parameters[i - 1] for i in molecule_indices]

                    angle_step = (angle_range[1] - angle_range[0]) / (num_structures - 1)
                    rotation_angles = [angle_range[0] + angle_step * i for i in range(num_structures)]

                    rotated_structures_list = []

                    for angle in rotation_angles:
                        temp_atoms = modified_atoms.copy()
                        for molecule, axis in zip(chosen_molecules, chosen_rotation_axes):
                            temp_atoms = rotate_molecules_v2(temp_atoms, molecule, axis, angle)
                        rotated_structures_list.append((temp_atoms, angle))

                    file_name = os.path.splitext(st.session_state.file_name)[0]

                    create_zip_with_rotated_structures(rotated_structures_list, file_name)

        if rotate_type == "Rotate Part of Molecules":
            st.header("Rotate Atoms in Molecule")

            # Gather user inputs for rotation using Streamlit widgets
            # molecules is a list of lists where each list contains indices from the atoms object that define a molecule
            molecule_indices = st.multiselect("Select molecule indices", options=range(1, len(molecules) + 1))

            if "rotation_parameters" not in st.session_state:
                st.session_state.rotation_parameters = [None] * len(molecules)
            if molecule_indices is not None:
                for i in molecule_indices:
                    st.subheader(f"Molecule {i}")

                    with st.form(key=f"molecule_{i}_form"):

                        atoms_to_rotate = st.multiselect("Enter the atom indices that require rotation",
                                                         options=[idx + 1 for idx in molecules[i - 1]])

                        axis_input = st.text_input("Enter crystal direction as h, k, l separated by spaces")

                        pivot_point = st.selectbox("Select the pivot point atom", options=[idx + 1 for idx in molecules[i - 1]])
                        angle = st.number_input("Enter rotation angle in degrees", step=1.0)

                        if st.form_submit_button(f"Set Parameters for Molecule {i}"):
                            hkl = np.array([int(val) for val in axis_input.split()])
                            lattice_vectors = modified_atoms.get_cell()
                            axis = np.dot(hkl, lattice_vectors)
                            axis /= np.linalg.norm(axis)

                            atoms_to_rotate_indices = [molecules[i - 1].index(atom - 1) for atom in atoms_to_rotate]
                            pivot_point_index = molecules[i - 1].index(pivot_point - 1)

                            st.session_state.rotation_parameters[i - 1] = (atoms_to_rotate_indices, axis, pivot_point_index, angle)

            if st.button("Apply Rotations"):
                chosen_molecules = [molecules[i - 1] for i in molecule_indices]
                chosen_rotation_parameters = [st.session_state.rotation_parameters[i - 1] for i in molecule_indices]

                for molecule, (atoms_to_rotate_indices, axis, pivot_point_index, angle) in zip(chosen_molecules,
                                                                                 chosen_rotation_parameters):
                    modified_atoms = rotate_molecules_v5(modified_atoms, molecule, axis, angle, pivot_point_index, atoms_to_rotate_indices)

                # Save modified atoms to temporary files
                output_suffix = "_rotated_some_atoms"
                file_name = os.path.splitext(st.session_state.file_name)[0]

                create_aims_download_file(modified_atoms, file_name, output_suffix)

                create_labelled_download_file(modified_atoms, file_name, output_suffix)

        if rotate_type == "Rotate by Dipole Moment":
            #This option aligns a molecule's dipole moment to a chosen crystal plane by rotating the molecule around its centroid
            st.header("Rotate Molecules to align with planes")

            # Gather user inputs for rotation using Streamlit widgets
            molecule_indices = st.multiselect("Select molecule indices", options=range(1, len(molecules) + 1))

            if molecule_indices is not None:



                if "alignment_planes" not in st.session_state:
                    st.session_state.alignment_planes = [None] * len(molecules)

                for i in molecule_indices:
                    st.subheader(f"Molecule {i}")

                    with st.form(key=f"molecule_{i}_alg_form"):

                        plane_input = st.text_input("Enter crystal plane as h, k, l separated by spaces")

                        if st.form_submit_button(f"Set Parameters for Molecule {i}"):
                            hkl = np.array([int(val) for val in plane_input.split()])
                            st.session_state.alignment_planes[i - 1] = hkl

                if st.button("Apply Alignments"):
                    chosen_molecules = [molecules[i - 1] for i in molecule_indices]
                    chosen_alignment_planes = [st.session_state.alignment_planes[i - 1] for i in molecule_indices]
                    lattice_vectors = modified_atoms.get_cell()

                    for molecule, miller_indices in zip(chosen_molecules, chosen_alignment_planes):
                        #calculate the dm
                        mol_obj = get_molecule_object(modified_atoms, molecule)
                        dm_vector, com = get_dm_direction(mol_obj)
                        #get the rotation matrix
                        rot_mat = align_vector_with_plane(dm_vector, lattice_vectors, miller_indices)
                        #get the axis
                        rot_ax, rot_ang = rotation_axis_and_angle_from_matrix_v2(rot_mat)
                        rot_ax_cr = crystal_direction_v3(rot_ax, lattice_vectors)
                        st.write(rot_ax_cr)
                        #supply it to the rotate_molecules
                        modified_atoms = rotate_molecules_v4(modified_atoms, molecule, mol_obj, rot_mat)

                    # Save modified atoms to temporary files
                    output_suffix = "_rotated_aligned"
                    file_name = os.path.splitext(st.session_state.file_name)[0]

                    create_aims_download_file(modified_atoms, file_name, output_suffix)

                    create_labelled_download_file(modified_atoms, file_name, output_suffix)

    if reflect_option:
        st.header("Reflect molecules on a plane")

        molecule_indices = st.multiselect("Select molecule indices", options=range(1, len(molecules) + 1))

        if "reflection_parameters" not in st.session_state:
            st.session_state.reflection_parameters = [None] * len(molecules)
        if molecule_indices is not None:
            for i in molecule_indices:
                st.subheader(f"Molecule {i}")

                with st.form(key=f"molecule_{i}_form"):

                    plane_input = st.text_input("Enter crystal plane as h, k, l separated by spaces")

                    # Add a multi-select list for atoms not to reflect
                    atom_labels = get_atom_labels(modified_atoms, molecules[i - 1])
                    atoms_not_to_reflect = st.multiselect("Select atom indices not to reflect (Optional)",
                                                          options=atom_labels, format_func=lambda x: x[1])

                    if st.form_submit_button(f"Set Parameters for Molecule {i}"):
                        hkl = np.array([int(val) for val in plane_input.split()])
                        local_indices = find_local_indices(molecules[i - 1],
                                                           [atom_idx for atom_idx, _ in atoms_not_to_reflect])
                        st.session_state.reflection_parameters[i - 1] = (hkl, local_indices)

                        # st.write(st.session_state.reflection_parameters[i - 1])

        if st.button("Apply Reflections"):
            chosen_molecules = [molecules[i - 1] for i in molecule_indices]
            chosen_reflection_parameters = [st.session_state.reflection_parameters[i - 1] for i in molecule_indices]

            for molecule, (hkl, not_to_reflect) in zip(chosen_molecules, chosen_reflection_parameters):
                mol_obj = get_molecule_object(modified_atoms, molecule)
                normal_vector, origin_point = plane_params_from_hkl(modified_atoms, hkl)
                modified_atoms = reflect_molecules(modified_atoms, molecule, mol_obj, normal_vector, origin_point,
                                                   not_to_reflect)

            # Save modified atoms to temporary files
            output_suffix = "_reflected"
            file_name = os.path.splitext(st.session_state.file_name)[0]

            create_aims_download_file(modified_atoms, file_name, output_suffix)

            create_labelled_download_file(modified_atoms, file_name, output_suffix)

    if translation_option:
        st.header("Translation")

        translate_type = st.selectbox("Select Translation Type", (
            "Molecules", "Atoms"))


        # scope_choice = st.selectbox("Do you want to translate molecules or atoms?", ("molecules", "atoms"))
        # st.session_state.scope_choice = scope_choice

        if translate_type == "Molecules":
            scope_choice = "molecules"
            selected_indices = st.multiselect("Select molecule indices to translate",
                                              range(1, len(molecules) + 1))

            with st.form(key="translation_form"):

                axes_choice = st.selectbox("Enter the axes for translation",
                                           ("x", "y", "z", "xy", "xz", "yz", "xyz", "custom"))

                if axes_choice == "custom":
                    custom_axis = st.text_input("Enter custom axis as x, y, z separated by spaces")
                    axis = np.array([float(val) for val in custom_axis.split()])
                    distance = st.number_input("Enter the translation distance", step=0.1)
                    translation_distances = {tuple(axis): distance}
                else:
                    translation_distances = {}
                    for axis in axes_choice:
                        distance = st.number_input(f"Enter the translation distance along {axis}-axis",
                                                   key=f"{axis}_translation", step=0.1)
                        translation_distances[axis] = distance

                if st.form_submit_button("Apply Translation"):
                    modified_atoms = translate_molecule(modified_atoms, molecules, scope_choice, selected_indices,
                                                        axes_choice,
                                                        translation_distances)

                    # Save modified atoms to temporary files
                    output_suffix = "_translated"

                    create_aims_download_file(modified_atoms, file_name, output_suffix)

                    create_labelled_download_file(modified_atoms, file_name, output_suffix)

                with st.expander("See structure"):
                    atoms_to_speck(modified_atoms, "translation")

        if translate_type == "Atoms":
            scope_choice = "atoms"
            selected_indices_string = st.text_input(
                "Enter atom indices to translate (separated by spaces or commas)")
            if selected_indices_string:
                selected_indices = [int(index.strip()) for index in
                                    selected_indices_string.replace(',', ' ').split() if index.strip()]

                with st.form(key="translation_form"):

                    axes_choice = st.selectbox("Enter the axes for translation",
                                               ("x", "y", "z", "xy", "xz", "yz", "xyz", "custom"))

                    if axes_choice == "custom":
                        custom_axis = st.text_input("Enter custom axis as x, y, z separated by spaces")
                        axis = np.array([float(val) for val in custom_axis.split()])
                        distance = st.number_input("Enter the translation distance", step=0.1)
                        translation_distances = {tuple(axis): distance}
                    else:
                        translation_distances = {}
                        for axis in axes_choice:
                            distance = st.number_input(f"Enter the translation distance along {axis}-axis",
                                                       key=f"{axis}_translation", step=0.1)
                            translation_distances[axis] = distance

                    if st.form_submit_button("Apply Translation"):
                        modified_atoms = translate_molecule(modified_atoms, molecules, scope_choice, selected_indices,
                                                            axes_choice,
                                                            translation_distances)

                        # Save modified atoms to temporary files
                        output_suffix = "_translated"

                        create_aims_download_file(modified_atoms, file_name, output_suffix)

                        create_labelled_download_file(modified_atoms, file_name, output_suffix)

                    with st.expander("See structure"):
                        atoms_to_speck(modified_atoms, "translation")

    if delete_option:
        st.header("Delete Molecules")
        with st.form(key="delete_form"):

            selected_indices = st.multiselect("Select molecule indices to delete",
                                              range(1, len(molecules) + 1))

            if st.form_submit_button("Apply Deletion"):
                modified_atoms = delete_molecules(modified_atoms, molecules, selected_indices)


                # Save modified atoms to temporary files
                output_suffix = "_deleted"

                create_aims_download_file(modified_atoms, file_name, output_suffix)

                create_labelled_download_file(modified_atoms, file_name, output_suffix)

            with st.expander("See structure"):
                atoms_to_speck(modified_atoms, "deletion")

    if symmetry_option:
        st.header("Symmetrize structure")
        with st.form(key="symmetry_form"):
            symprec_lower = st.number_input("Enter the lower bound for tolerance", value=1e-3, step=1e-3, format="%.4f")
            symprec_upper = st.number_input("Enter the upper bound for tolerance", value=1e-1, step=1e-3, format="%.4f")
            symprec_list = np.linspace(symprec_lower, symprec_upper, 6)
            angle_tol = st.number_input("Enter a tolerance for angles", value=5.0, step=1e-3, format="%.4f")

            if symprec_lower > symprec_upper:
                st.error("Lower bound should be less than or equal to the upper bound.")

            form_submitted = st.form_submit_button("Get Space Groups")

        # Update space groups if form_submitted is True or if space groups have not been calculated yet
        if form_submitted or 'space_groups' not in st.session_state:
            # Here, calculate_space_groups should return both symprec_list and space_groups
            st.session_state['symprec_list'], st.session_state['space_groups'] = calculate_space_groups(modified_atoms,
                                                                                                        symprec_lower,
                                                                                                        symprec_upper,
                                                                                                        angle_tol)
            st.session_state['space_group_strings'] = get_space_group_strings(st.session_state['symprec_list'],
                                                                              st.session_state['space_groups'])

        # Ensure that 'space_group_strings' and 'symprec_list' are available for the dropdown and button actions
        if 'space_group_strings' in st.session_state and 'symprec_list' in st.session_state:
            selected_string = st.selectbox("Select the desired space group",
                                          options=st.session_state.space_group_strings,
                                          index=0)

            if st.button("Generate CIF"):
                try:
                    file_name_m = os.path.splitext(file_name)[0]
                    output_cif_file = f"{file_name_m}_high_symm.cif"
                    selected_symprec = extract_symprec_from_string(selected_string)
                    pymatgen_structure = generate_symmetrized_structure(modified_atoms, selected_symprec, angle_tol)

                    cif_writer = CifWriter(pymatgen_structure, symprec=selected_symprec, angle_tolerance=st.session_state.angle_tol)

                    with tempfile.NamedTemporaryFile(mode="w+", suffix=".cif", delete=False) as output_file:
                        cif_writer.write_file(output_file.name)  # Write the content to the temporary file
                        output_file.seek(0)
                        output_content = output_file.read()
                        st.markdown(get_download_link(f"{output_cif_file}", output_content), unsafe_allow_html=True)
                except ValueError as e:
                    st.error(f"An error occurred when processing the selected space group: {e}")
                except Exception as e:
                    st.error(f"An unexpected error occurred: {e}")

    if create_cent_option:
        st.header("Create Idealized Structure")

        atoms_idl = None


        inorganic_indices_acent = st.multiselect("Enter inorganic molecule indices, separated by spaces: ",
                                                options=range(1, len(molecules) + 1), key='initial_cent')

        if inorganic_indices_acent:
            initial_organic_acent, initial_inorganic_acent = generate_substructure(modified_atoms, molecules,
                                                                                 inorganic_indices_acent)
            # create_labelled_download_file(initial_inorganic_acent, "initial_inorganic", "")



            file_name_ac = os.path.splitext(file_name)[0]

            output_cif_file_acent = f"{file_name_ac}_inorganic.cif"
            # standardized_atoms, selected_symprec = write_cif_with_higher_symmetry(modified_atoms, symprec_lower,
            #                                                                       symprec_upper, selected_index)

            lattice, scaled_positions, numbers = spglib.standardize_cell(initial_inorganic_acent, to_primitive=False, no_idealize=False,
                                                                         symprec=0.0001)

            standardized_atoms = Atoms(cell=lattice, scaled_positions=scaled_positions, numbers=numbers)

            pymatgen_structure = AseAtomsAdaptor.get_structure(standardized_atoms)

            cif_writer = CifWriter(pymatgen_structure, symprec=0.0001)

            with tempfile.NamedTemporaryFile(mode="w+", suffix=".cif", delete=False) as output_file:
                cif_writer.write_file(output_file.name)  # Write the content to the temporary file
                output_file.seek(0)
                output_content = output_file.read()
                st.markdown(get_download_link(f"{output_cif_file_acent}", output_content), unsafe_allow_html=True)

            # create_labelled_download_file(initial_organic_acent, file_name_ac, "_acentric_organic")
            create_aims_download_file(initial_organic_acent, file_name_ac,"_organic")

            file_buffer_idl = st.file_uploader("Upload the idealized inorganic structure (Do a PseudoSymmetry analysis)",
                                               type=[".in", ".cif", ".next_step"])
            if file_buffer_idl:
                file_name_idl = file_buffer_idl.name
                file_format_idl = get_file_format(file_name_idl)
                atoms_idl, molecules_idl, modified_symbols_idl = initialize_structure_v2(file_buffer_idl,
                                                                                         file_format_idl)

            if initial_organic_acent is not None and atoms_idl is not None:
                molecules_io_acent = detect_molecules(initial_organic_acent)
                modified_symbols_acent = [f"{atom.symbol}{i + 1}" for i, atom in enumerate(initial_organic_acent)]

                print_detected_molecules(modified_symbols_acent, molecules_io_acent, "initial organic sublattice")

                rotate_indices_acent = st.multiselect(
                    "Enter molecular indices you want to rotate, separated by spaces: ",
                    options=range(1, len(molecules_io_acent) + 1), key='rotate_mol')

                if rotate_indices_acent:
                    if "rotation_axes" not in st.session_state:
                        st.session_state.rotation_axes = [None] * len(molecules_io_acent)

                    for i in rotate_indices_acent:
                        st.subheader(f"Molecule {i}")

                        with st.form(key=f"molecule_{i}_form"):
                            hkl_input = st.text_input("Enter crystal direction as h, k, l separated by spaces")

                            if st.form_submit_button(f"Set Axis for Molecule {i}"):
                                hkl = np.array([int(val) for val in hkl_input.split()])
                                lattice_vectors = initial_organic_acent.get_cell()
                                axis = np.dot(hkl, lattice_vectors)
                                axis /= np.linalg.norm(axis)

                                st.session_state.rotation_axes[i - 1] = axis

                generate_structure_button = st.button("Generate Structure")

                if generate_structure_button:
                    chosen_rotation_axes = [st.session_state.rotation_axes[i - 1] for i in rotate_indices_acent]
                    chosen_molecules = [molecules_io_acent[i - 1] for i in rotate_indices_acent]
                    rotation_angle = 180

                    rotated_organic_structure = initial_organic_acent.copy()
                    for molecule, axis in zip(chosen_molecules, chosen_rotation_axes):
                        rotated_organic_structure = rotate_molecules_v2(rotated_organic_structure, molecule, axis,
                                                                        rotation_angle)

                    # Merge O2 and I2
                    cent_str = merge_structures(rotated_organic_structure, atoms_idl)
                    create_aims_download_file(cent_str, file_name, "_centric")

    if com_option:
        st.header('Get center of mass of molecules')
        # scale_choice = st.checkbox("Scaled (Fractional) co-ordinates")
        scale_choice = False
        df_centroids, df_distance_matrix, lattice_vectors, df_merged = get_distance_matrix(modified_atoms, molecules)


        # Print the distances
        st.dataframe(df_merged, use_container_width=True)


        # Generate 3D plot using Plotly
        fig = px.scatter_3d(df_centroids, x='a', y='b', z='c', text=df_centroids.index, color=df_centroids.index,
                            opacity=0.7, hover_name=df_centroids.index)
        fig.update_layout(scene=dict(xaxis_title='a', yaxis_title='b', zaxis_title='c'), title='Centroids 3D Plot',
                          width=600, height=600)

        # Draw the unit cell box
        scaled_lattice_vectors = np.array([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
        # Create the centroids and distance matrix plots
        box_vectors = scaled_lattice_vectors if scale_choice else lattice_vectors
        centroids_fig = create_3d_scatter_plot(df_centroids, 'Centroids', box_vectors)
        # distance_matrix_fig = create_3d_scatter_plot(df_distance_matrix, 'Distance Matrix', box_vectors)

        # Use Streamlit column containers to display the plots
        st.plotly_chart(centroids_fig, use_container_width=True)
        # col1, col2 = st.columns(2)
        # with col1:
        #     st.plotly_chart(centroids_fig, use_container_width=True)
        # with col2:
        #     st.plotly_chart(distance_matrix_fig, use_container_width=True)

        # Call the function with the new method
        sym_part = st.button("Search for Symmetric Partners")

        if sym_part:
            try:
                symmetric_partners = find_closest_partners(df_centroids, lattice_vectors, initial_threshold=1e-3, max_iterations=1000)
                for key, value in symmetric_partners.items():
                    st.markdown(value)

            except Exception as e:
                st.error(f"Error: {e}")


        # translations_to_restore_symmetry, symmetry_output = find_translation_to_restore_symmetry(df_centroids,
        #                                                                                          lattice_vectors)
        # st.write("Translations required to restore inversion symmetry:", translations_to_restore_symmetry)
        # for line in symmetry_output:
        #     st.write(line)

        # col1, col2 = st.columns(2)
        # col1.plotly_chart(fig1, use_container_width=True)
        # col2.plotly_chart(fig2, use_container_width=True)

    if dm_option:
        st.header("Get dipole moment direction")

        # Gather user inputs for rotation using Streamlit widgets
        molecule_indices = st.multiselect("Select molecule indices", options=range(1, len(molecules) + 1))
        # Add widget to get camera position
        x_pos = st.number_input("Camera X position", value=0.0)
        y_pos = st.number_input("Camera Y position", value=0.0)
        z_pos = st.number_input("Camera Z position", value=0.0)

        if st.button("Get direction"):
            chosen_molecules = [molecules[i - 1] for i in molecule_indices]
            direction_dict = []

            # Construct the molecule object and calculate the dipole moment directions
            for mol_index, molecules in zip(molecule_indices, chosen_molecules):
                mol_obj = get_molecule_object(modified_atoms, molecules)
                dm_vector, com = get_dm_direction(mol_obj)

                # crystal_dir = get_perpendicular_crystal_directions(dm_vector, modified_atoms)     # direction perpendicular to the dipole moment
                crystal_dir, fract_com = get_crystal_direction(dm_vector, modified_atoms, com)
                direction_dict.append((mol_index, com, dm_vector, crystal_dir))

            # Convert the direction_dict list to a pandas DataFrame
            direction_df = pd.DataFrame(direction_dict,
                                        columns=['Molecule Index', 'Center of Mass', 'Dipole Moment Vector',
                                                 'Crystal Direction'])

            # Display the DataFrame using Streamlit
            # st.write(direction_df)
            # if st.button("Set camera"):
            camera_pos = [x_pos, y_pos, z_pos]
            dm_plot = plot_dipole_moment_vectors(direction_df, modified_atoms, chosen_molecules, camera_pos)
            st.plotly_chart(dm_plot)

            #

    if distance_option:
        st.header("Calculate atomic distances")

        # User input for atomic symbols
        first_atom = st.text_input('Enter the symbol of the first atom (A):', value="Pb")
        second_atoms = st.text_input('Enter the symbol of the second atom (B):', value="I")

        min_cutoff, max_cutoff = st.slider(
            "Set cut-off range for searching the atoms",
            min_value=0.0,
            max_value=10.0,
            value=(0.0, 3.5),  # Default values for min and max
            step=0.1,
        )

        if st.button('Calculate'):
            found_distances = find_third_atom_distances_with_cutoff(modified_atoms, first_atom, second_atoms, min_cutoff, max_cutoff)

            st.dataframe(found_distances, use_container_width=True, hide_index=True)

    if distortion_option:
        st.header("Calculate octahedral distortions")

        # User input for atomic symbols
        center_atom = st.text_input('Enter the symbol of the center atom (A):', value="Pb")
        surrounding_atoms = st.text_input('Enter the symbol of the surrounding atoms (B):', value="I")

        # User input for type of distortion(s)
        distortion_type = st.selectbox(
            'Select the type of distortion to calculate:',
            ('Bond distance variance', 'Angle variance', 'Bridging angle(s)', 'In and out deviations', 'Beta parameter', 'all')
        )

        # Button for confirmation
        if st.button('Calculate'):
            super_atoms, periodic_image_dict = filter_atoms_by_symbols_and_extend(modified_atoms, center_atom,
                                                                                  surrounding_atoms)
            AB6_octahedra, AB_distances = identify_AB_groups(super_atoms, center_atom, surrounding_atoms)

            unq_AB_distances = filter_unique_distances(AB_distances)

            octahedral_distances = find_matching_distances(modified_atoms, center_atom, surrounding_atoms, unq_AB_distances)

            st.markdown(f'**Distance of {center_atom} - {surrounding_atoms} bonds in octahedra**')
            st.dataframe(octahedral_distances, use_container_width=True, hide_index=True)

            # Create a dictionary to map distortion types to functions
            distortion_mapping = {
                'Bond distance variance': lambda x, y: calculate_bond_distance_variance(x, y),
                'Angle variance': lambda x, y: calculate_angle_variance(x, y),
                'Bridging angle(s)': lambda x, y: calculate_unique_ABA_angles(x, y),
                'In and out deviations': lambda x, y: calculate_in_out_planes(x, y),
            }

            # Call the respective function based on the selected option
            output_list = []
            if distortion_type == 'all':
                for func_name, func in distortion_mapping.items():
                    result = func(AB6_octahedra, super_atoms)
                    if func_name == 'Bridging angle(s)':
                        angle, beta = result
                        output_list.append(f'''   **Bridging angle(s):** :violet[{str(list(angle.keys())[0:]).strip('[]')}]  ''')
                        output_list.append(f'''   **Beta parameter:** :violet[{str(beta).strip('[]')}]  ''')
                    elif func_name == 'In and out deviations':
                        output_list.append(f'''   **In and Out of plane deviations:**  ''')
                        for angle, deviations in result.items():
                            output_list.append(f'''   **Bridging angle:** :gray[{angle}]   ''')
                            output_list.append(f'''   In-plane deviation: :violet[{deviations['in_plane']:.3f}]   ''')
                            output_list.append(f'''   Out-of-plane deviation: :violet[{deviations['out_plane']:.3f}]   ''')
                    else:
                        output_list.append(f"  **{func_name}:** :violet[{str(result).strip('[]')}]  ")
            else:
                result = distortion_mapping[distortion_type](AB6_octahedra, super_atoms)
                if distortion_type == 'Bridging angle(s)':
                    angle, beta = result
                    output_list.append(f'''   **Bridging angle(s):** :violet[{str(list(angle.keys())[0:]).strip('[]')}]  ''')
                    output_list.append(f'''   **Beta parameter:** :violet[{str(beta).strip('[]')}]  ''')
                elif distortion_type == 'In and out deviations':
                    output_list.append(f'''   **In and Out of plane deviations:**  ''')
                    for angle, deviations in result.items():
                        output_list.append(f'''   **Bridging angle:** :gray[{angle}]   ''')
                        output_list.append(f'''   In-plane deviation: :violet[{deviations['in_plane']:.3f}]   ''')
                        output_list.append(f'''   Out-of-plane deviation: :violet[{deviations['out_plane']:.3f}]   ''')
                else:
                    output_list.append(f"  {distortion_type}: **{str(result).strip('[]')}**  ")

            st.markdown("\n\n".join(output_list))

if interpolate_option:
    st.header("Interpolate Structures")
    file_buffer1 = st.file_uploader("Upload an initial structure file (AIMS or CIF)", type=[".in", ".cif"],
                                    key="file_buffer1")
    file_buffer2 = st.file_uploader("Upload a final structure file (AIMS or CIF)", type=[".in", ".cif"],
                                    key="file_buffer2")

    if file_buffer1 is not None and file_buffer2 is not None:

        atoms1, atoms2, file_name1, file_name2 = process_uploaded_files(file_buffer1, file_buffer2)

        if atoms1 is not None and atoms2 is not None:
            n = st.number_input("Enter the number of interpolated structures to generate:", min_value=1,
                                step=1)

            # Convert ase atoms to pymatgen structures
            initial_structure = AseAtomsAdaptor.get_structure(atoms1)
            final_structure = AseAtomsAdaptor.get_structure(atoms2)

            # Initialize the StructureMatcher with primitive_cell set to False
            sm = StructureMatcher(primitive_cell=False)

            # Match two structures
            final_structure_reordered = sm.get_s2_like_s1(initial_structure, final_structure)

            label_atoms = st.checkbox("Do you want labelled atoms for checking?")

            if label_atoms:
                file_name_o1 = file_name1 + "_labelled"
                file_name_o2 = file_name2 + "_reordered_labelled"
                generate_labelled_cif(initial_structure, file_name_o1)
                generate_labelled_cif(final_structure_reordered, file_name_o2)

    if st.button("Generate Interpolated Structures"):
        if atoms1 is not None and atoms2 is not None:
            try:
                # Interpolate between the two structures
                interpolated_structures = initial_structure.interpolate(final_structure_reordered,
                                                                        nimages=n,
                                                                        autosort_tol=0.5,
                                                                        interpolate_lattices=True)

                # Convert pymatgen structures back to ase atoms
                interpolated_atoms = [AseAtomsAdaptor.get_atoms(structure) for structure in
                                      interpolated_structures]

                # Save interpolated structures to a temporary ZIP file
                create_interpolated_structures_zip(interpolated_atoms)

            except Exception as e:
                st.error(f"Error: {e}")

if trans_rotate_option:
    st.header("Translate Inorganic and Rotate Organic Subunits")
    file_buffer1 = st.file_uploader("Upload an initial structure file (AIMS or CIF)", type=[".in", ".cif"],
                                    key="file_buffer1")
    file_buffer2 = st.file_uploader("Upload a final structure file (AIMS or CIF)", type=[".in", ".cif"],
                                    key="file_buffer2")

    if file_buffer1 is not None and file_buffer2 is not None:

        atoms1, molecules1 = process_file_and_print_molecules(file_buffer1, "initial structure")

        inorganic_indices1 = st.multiselect("Enter inorganic molecule indices, separated by spaces: ",
                                            options=range(1, len(molecules1) + 1), key='initial')

        initial_organic, initial_inorganic = generate_substructure(atoms1, molecules1, inorganic_indices1)

        atoms2, molecules2 = process_file_and_print_molecules(file_buffer2, "final structure")

        inorganic_indices2 = st.multiselect("Enter inorganic molecule indices, separated by spaces: ",
                                            options=range(1, len(molecules2) + 1), key='final')

        final_organic, final_inorganic = generate_substructure(atoms2, molecules2, inorganic_indices2)

        # Let user decide whether to show download links for initial/final organic/inorganic files
        show_download_links = st.checkbox("Show download links for initial/final organic/inorganic files")

        if show_download_links:
            create_labelled_download_file(initial_inorganic, "initial_inorganic", "")
            create_labelled_download_file(initial_organic, "initial_organic", "")
            create_labelled_download_file(final_inorganic, "final_inorganic", "")
            create_labelled_download_file(final_organic, "final_organic", "")

        if inorganic_indices1 and inorganic_indices2:

            st.subheader("Starting Interpolation")
            n = st.number_input("Enter the number of interpolated structures to generate:", min_value=1,
                                step=1)
            n = (n + 1)

            molecules_io = detect_molecules(initial_organic)
            modified_symbols = [f"{atom.symbol}{i + 1}" for i, atom in enumerate(initial_organic)]

            print_detected_molecules(modified_symbols, molecules_io, "initial organic sublattice")

            rotate_indices = st.multiselect("Enter molecular indices you want to rotate, separated by spaces: ",
                                            options=range(1, len(molecules_io) + 1), key='rotate_mol')

            use_custom_axis = st.checkbox("Use custom rotation axis")

            axis_input = st.text_input(
                "Enter custom axis as x, y, z separated by spaces") if use_custom_axis else None
            axis = axis_input.split() if axis_input else st.selectbox("Select rotation axis",
                                                                      options=["x", "y", "z"])

            if use_custom_axis:
                axis = np.array([float(val) for val in axis_input.split()])
            else:
                axis_dict = {'x': [1, 0, 0], 'y': [0, 1, 0], 'z': [0, 0, 1]}
                axis = axis_dict[axis]

            if st.button("Generate Interpolated Structures"):
                if atoms1 is not None and atoms2 is not None:
                    try:
                        # Rotate the organic
                        rotated_organic_structures = rotate_organic_molecules(initial_organic,molecules_io, n, rotate_indices, axis)       #180 deg rotated structure is the last one


                        # Translate the inorganic
                        if rotated_organic_structures is not None:

                            inorganic_interpolated_structures = interpolate_inorganic_lattice(initial_inorganic,
                                                                                              final_inorganic, n)


                            if rotated_organic_structures is not None and inorganic_interpolated_structures is not None:
                                st.subheader("Here are the interpolated structures:")
                                # Save interpolated structures to a temporary ZIP file
                                merge_and_create_zip(rotated_organic_structures, inorganic_interpolated_structures)




                    except Exception as e:
                        st.error(f"Error: {e}")

if plot_polarization_option:
    st.title("Polarization Analysis")

    uploaded_files = st.file_uploader("Upload one or more AIMS output files (.out)", accept_multiple_files=True,
                                      type=".out")

    if uploaded_files:
        # Create an empty DataFrame to store the extracted data
        data = pd.DataFrame(columns=["File", "Parameter", "Px", "Py", "Pz"])

        # Iterate over the uploaded files and collect the parameter values
        file_parameters = {}
        for uploaded_file in uploaded_files:
            parameter = st.number_input(f"Enter the parameter value for {uploaded_file.name}", step=1.0)
            file_parameters[uploaded_file.name] = parameter

        parameter_name = st.text_input("Enter the name of the parameter:")
        parameter_unit = st.text_input("Enter the unit of the parameter:")

        if st.button("Process Files"):
            # Iterate over the uploaded files and update the DataFrame
            for uploaded_file in uploaded_files:
                file_content = uploaded_file.read().decode("utf-8")
                parameter = file_parameters[uploaded_file.name]

                # Extract the polarization values from the file content
                px, py, pz = extract_polarization(file_content)

                #Extract the total energy values from the file content
                Et = extract_totalenergy(file_content)

                # Append the extracted data to the DataFrame
                data = data.append({"File": uploaded_file.name, "Parameter": parameter, "Px": px, "Py": py, "Pz": pz, "Et": Et},
                                   ignore_index=True)


        flip_plot = st.checkbox("Flip plot")
        if flip_plot and not data.empty:
            data[["Px", "Py", "Pz"]] *= -1

        if not data.empty:
            data = data.sort_values("Parameter")
            with st.expander("See Datapoints"):
                st.write(data)
                csv_link, txt_link, tsv_link = data_download_links(data, 'datapoints')
                st.markdown(csv_link, unsafe_allow_html=True)
            with st.expander("See Plots"):
                plot_pol_figure(data, parameter_name, parameter_unit)


            # plot_pol_figure(data, parameter_name, parameter_unit)




            # if exp_option:
    # tab1, tab2, tab3 = st.tabs(["Cat", "Dog", "Owl"])
    #
    # with tab1:
    #     st.header("A cat")
    #     st.image("https://static.streamlit.io/examples/cat.jpg", width=200)
    #
    # with tab2:
    #     st.header("A dog")
    #     st.image("https://static.streamlit.io/examples/dog.jpg", width=200)
    #
    # with tab3:
    #     st.header("An owl")
    #     st.image("https://static.streamlit.io/examples/owl.jpg", width=200)

    # with st.container():
    #     st.write("This is inside the container")
    #
    #     # You can call any Streamlit command, including custom components:
    #     st.bar_chart(np.random.randn(50, 3))
    #
    # st.write("This is outside the container")

if plot_pdos_option:
    st.title("Plot PDOS")

    # File uploader for all DOS files
    uploaded_files = st.file_uploader("Upload Total DOS and element DOS files:", type=['dat', 'txt'],
                                      accept_multiple_files=True)

    # Input for shift value
    shift = float(st.number_input("Enter shift value:", value=0.00))
    st.session_state.shift = shift

    # Input field for plot_range variable
    plot_range = st.slider("Select plot range:", min_value=-30.0, max_value=30.0, value=(-2.0, 5.0), step=1.0)


    # Plot button
    plot_button = st.button("Plot")

    # Process the uploaded files to create dos_data dictionary
    if plot_button:
        if uploaded_files:
            dos_data = {}

            for file in uploaded_files:
                if file.name == "KS_DOS_total.dat":
                    dos_data['Total'] = np.loadtxt(file)
                else:
                    # Extract element name from the file name
                    element_name = re.match(r'(\w+)_l_proj_dos.dat', file.name)
                    if element_name:
                        element_name = element_name.group(1)
                        dos_data[element_name] = np.loadtxt(file)

            # Check if Total DOS data is provided
            if 'Total' in dos_data:
                # Call the plot_pdos_streamlit function and display the plot
                fig = plot_pdos_streamlit(dos_data, st.session_state.shift, plot_range)
                st.plotly_chart(fig)
            else:
                st.error("Total DOS file (KS_DOS_total.dat) not found in the uploaded files.")
        # else:
        #     st.warning("Please upload the required files.")

if plot_bs_option:
    st.title("Plot Bandstructure")

    # File uploader
    uploaded_files = st.file_uploader("Upload_files:", type=['in', 'out'], accept_multiple_files=True)

    # Plot range input
    plot_range = st.slider("Select plot range:", min_value=-30.0, max_value=30.0, value=(-2.0, 5.0), step=1.0)

    # Plot color
    plot_color = st.text_input("Color for the bandstructure", value='blue')

    # Plot button
    plot_button = st.button("Plot")

    # Process the uploaded files to create dos_data dictionary
    if plot_button:
        if uploaded_files:
            ymin, ymax = plot_range

            with st.spinner('Processing files...'):
                temp_dir = Path("temp_band_files")
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
                temp_dir.mkdir()

                for uploaded_file in uploaded_files:
                    with open(temp_dir / uploaded_file.name, "wb") as f:
                        f.write(uploaded_file.getvalue())

                os.chdir(temp_dir)

                # Call scan_CBM.py and extract the shift value
                scan_cbm_output = subprocess.check_output("python ./scan_CBM.py", shell=True,
                                                          stderr=subprocess.DEVNULL).decode('utf-8')

                for line in scan_cbm_output.splitlines():
                    if "VBM energy:" in line:
                        shift = float(line.split(":")[1].split("eV")[0].strip())
                        break

                plot_band_output = subprocess.check_output(
                    f"python3 ./plot_band.py {shift} {ymin} {ymax} output_band.png {plot_color}", shell=True,
                    stderr=subprocess.DEVNULL).decode('utf-8')

                # Layout
                col1, col2 = st.columns([1, 4])

                with col1:
                    with st.expander("Band Edge Scan Output"):
                        # Band Edge Scan Results
                        # st.subheader("Band Edge Scan")
                        formatted_scan_cbm = scan_cbm_output.replace("\n", "<br>")
                        scan_cbm_box = f'<div style="height:220px; text-align: center; width:100%; overflow:auto; background-color:#333333; color:#FFFFFF; border-radius:10px; padding: 0px;"><pre>{formatted_scan_cbm}</pre></div>'
                        st.markdown(scan_cbm_box, unsafe_allow_html=True)

                    # Space
                    st.empty()

                    # Bandstructure Plot Results
                    with st.expander("Bandstructure Plot Output"):
                        formatted_plot_band = plot_band_output.replace("\n", "<br>")
                        plot_band_box = f'<div style="height:220px; text-align: center; width:100%; overflow:auto; background-color:#333333; color:#FFFFFF; border-radius:10px; padding: 0px;"><pre>{formatted_plot_band}</pre></div>'
                        st.markdown(plot_band_box, unsafe_allow_html=True)

                with col2:
                    st.subheader("Generated Bandstructure")
                    st.image("output_band.png", caption=" ", use_column_width=True)

                with open("output_band.png", "rb") as f:
                    btn = st.download_button(
                        label="Download Bandstructure Image",
                        data=f,
                        file_name="output_band.png",
                        mime="image/png"
                    )

                os.chdir("..")
                shutil.rmtree(temp_dir)
        else:
            st.warning("Please upload files before plotting.")

if plot_spin_option:
    st.title("Plot Spin Texture")
    st.title("Still in development...")

    # File uploader
    uploaded_files = st.file_uploader("Upload_files:", type=['dat'], accept_multiple_files=False)

    # Plot state input
    plot_range = st.slider("Select plot range:", min_value=-30.0, max_value=30.0, value=(-2.0, 5.0), step=1.0)




if deviation_calculation_option:
    st.title("Calculate deviation")

    file_buffer1 = st.file_uploader("Upload an initial structure file (AIMS or CIF)", type=[".in", ".cif"],
                                    key="file_buffer1")
    file_buffer2 = st.file_uploader("Upload a final structure file (AIMS or CIF)", type=[".in", ".cif"],
                                    key="file_buffer2")

    if file_buffer1 is not None and file_buffer2 is not None:

        atoms1, atoms2, file_name1, file_name2 = process_uploaded_files(file_buffer1, file_buffer2)

        if atoms1 is not None and atoms2 is not None:
            # Convert ase atoms to pymatgen structures
            initial_structure = AseAtomsAdaptor.get_structure(atoms1)
            final_structure = AseAtomsAdaptor.get_structure(atoms2)

            # Extract lattice parameters
            lattice_parameters = ['a (Å)', 'b (Å)', 'c (Å)', 'alpha (°)', 'beta (°)', 'gamma (°)', 'volume (Å^3)']
            lattice_parameter_keys = ['a', 'b', 'c', 'alpha', 'beta', 'gamma', 'volume']
            initial_params = [getattr(initial_structure.lattice, p) for p in lattice_parameter_keys]
            final_params = [getattr(final_structure.lattice, p) for p in lattice_parameter_keys]

            # Calculate percentage deviations
            deviations = [(final - initial) / initial * 100 for initial, final in zip(initial_params, final_params)]

            # Prepare data for the table
            table_data = list(zip(lattice_parameters, initial_params, final_params, deviations))

            # Create dataframe
            df = pd.DataFrame(table_data,
                              columns=["Lattice Parameter", "Initial Value", "Final Value", "Deviation (%)"])

            # Display the dataframe
            st.dataframe(df, use_container_width=True, hide_index=True)

if MD_option:
    st.title("Analyze AIMS Molecular Dynamics (MD) Output files")

    file_buffer_md = st.file_uploader("Upload MD output files", type=[".out"], accept_multiple_files=True,
                                      key="file_buffer_md")

    if file_buffer_md:
        df = process_streams(file_buffer_md)
        plot_data(df)


        # Convert the DataFrame to a CSV string
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download data as CSV",
            data=csv,
            file_name="md_output.csv",
            mime="text/csv"
        )

        # Button to generate files
        if st.button("Generate files"):
            # zip_file, spt_file, movie_file = run_perl_script(file_buffer_md)
            zip_file, spt_file = run_perl_script(file_buffer_md)

            # Provide native download option for zip_file
            with open(zip_file, "rb") as f:
                zip_data = f.read()
            st.download_button(
                label=f"Download {zip_file}",
                data=zip_data,
                file_name="geometries.zip",
                mime="application/zip"
            )

            # Remove the files after they have been downloaded
            os.remove(zip_file)
            os.remove(spt_file)
            os.remove("joined_file.out")
            # os.remove(movie_file)



def handle_h_bond_analysis(u):
    donor_atom = st.text_input("Enter donor atom (e.g., O)")
    acceptor_atom = st.text_input("Enter acceptor atom (e.g., Br)")
    da_cutoff = st.number_input("Enter donor-acceptor cutoff", min_value=0.0, max_value=10.0, step=0.1)
    angle_cutoff = st.number_input("Enter angle cutoff", min_value=0, max_value=180, step=1)

    if st.button('Do H-bond analysis'):
        try:
            # st.write("Building universe...")
            # u = build_universe_from_dir('frames_dir', timestep=timestep)
            st.write("Running hydrogen bond analysis...")
            h = hydrogen_bond_analysis(u, donor_atom, acceptor_atom, da_cutoff, angle_cutoff)
            st.write("Plotting hydrogen bond distances...")
            _, _, counts_fig = plot_hbond_data(h, u)

            st.plotly_chart(counts_fig, use_container_width=True)

            # col1, col2, col3 = st.columns(3)
            # Create 2x2 grid using Streamlit's column feature
            # col1, col_space, col2 = st.columns([1, 0.1, 1])
            # # col1, col2 = st.columns(2)
            # col3, col_space, col4 = st.columns([1, 0.1, 1])
            # with col1:
            #     st.plotly_chart(distances_fig)
            # with col2:
            #     st.plotly_chart(counts_fig)
            # with col3:
            #     st.plotly_chart(angles_fig)

        except Exception as e:
            st.write(f"Error: {str(e)}")
    pass

def handle_distance_analysis(u):
    distance_analysis_type = st.selectbox("Select Analysis Type", ("Overall statistics", "Individual tracking"))
    if distance_analysis_type == "Overall statistics":
        atom1 = st.text_input("Enter first atom for distance analysis")
        atom2 = st.text_input("Enter second atom for distance analysis")
        standard_distance = st.number_input("Enter a standard distance for comparison: ", min_value=0.0, max_value=10.0,
                                            step=0.01)

        if st.button('Do distance analysis'):
            try:
                # st.write("Building universe...")
                # u = build_universe_from_dir('frames_dir', timestep=timestep)
                st.write("Running minimum distance analysis...")
                fig, dist_df = plot_and_return_min_distances(u, atom1, atom2, standard_distance)
                fig_heatmap_png = generate_weighted_pair_probability_heatmap(dist_df)
                fig_heatmap = generate_weighted_pair_probability_heatmap_plotly(dist_df)

                # Use st.columns to display figures side by side
                col1, col_space, col2 = st.columns([1, 0.4, 1])
                with col1:
                    st.write("Minimum Distances Plot:")
                    st.plotly_chart(fig)
                with col2:
                    st.write("Weighted Pair Formation Probability Plot:")
                    st.plotly_chart(fig_heatmap)
                # Provide a download link for the PNG image below the heatmap
                st.markdown(get_figure_image_download_link(fig_heatmap_png), unsafe_allow_html=True)


            except Exception as e:
                st.write(f"Error: {str(e)}")


    elif distance_analysis_type == "Individual tracking":

        atom_pairs = []

        num_pairs = st.number_input("Enter the number of atom pairs for tracking:", min_value=1, max_value=10, step=1)
        standard_distance = st.number_input("Enter a standard distance for comparison: ", min_value=0.0, max_value=10.0,
                                            step=0.01)

        for i in range(num_pairs):
            atom_index1 = int(st.number_input(f"Enter index of first atom for pair {i + 1}:"))

            atom_index2 = int(st.number_input(f"Enter index of second atom for pair {i + 1}:"))
            atom_pairs.append((atom_index1, atom_index2))
        if st.button('Do individual tracking analysis'):
            try:
                st.write("Running individual tracking analysis...")
                fig = plot_atom_distances_over_time(u, standard_distance, *atom_pairs)

                # Display the plot
                st.plotly_chart(fig)


            except Exception as e:

                st.write(f"Error: {str(e)}")

    pass



def handle_rdf_analysis(u):
    rdf_analysis_type = st.selectbox("Select Analysis Type", ("Overall statistics", "Group tracking"))
    if rdf_analysis_type == "Overall statistics":
        atom1 = st.text_input("Enter first atom type for rdf analysis")
        atom2 = st.text_input("Enter second atom type for rdf analysis")
        bin_size = st.number_input("Enter bin size (optional):", value=75)
        min_dist, max_dist = st.slider(
            "Set cut-off range for distance",
            min_value=0.0,
            max_value=20.0,
            value=(0.0, 15.0),  # Default values for min and max
            step=0.1,
        )

        if st.button('Do rdf analysis'):
            try:

                st.spinner("Running rdf analysis...")
                rdf_df = calculate_rdf_mda(u, atom1, atom2, bins=bin_size, range=(min_dist, max_dist), start=None, stop=None, step=None, verbose=False)
                # st.dataframe(rdf_df)

                # Create and display the plot after rdf_df is generated.
                rdf_plot = plot_rdf(rdf_df)
                st.plotly_chart(rdf_plot, use_container_width=True)

                # Create and display the download button for the rdf_df data.
                csv_data = rdf_df.to_csv(index=False).encode()
                st.download_button("Download rdf data as CSV", csv_data, file_name="rdf_data.csv", mime="text/csv")


            except Exception as e:
                st.write(f"Error: {str(e)}")



    elif rdf_analysis_type == "Group tracking":

        group_pairs = []

        num_pairs = st.number_input("Enter the number of atom group pairs for tracking:", min_value=1, max_value=10, step=1)

        min_dist, max_dist = st.slider(
            "Set cut-off range for distance",
            min_value=0.0,
            max_value=20.0,
            value=(0.0, 15.0),  # Default values for min and max
            step=0.1,
        )

        for i in range(num_pairs):
            # Get atom indices for the two atom groups using space-separated input
            atom_indices_g1 = st.text_input(
                f"Enter indices (space-separated) for atoms in pair {i + 1} group 1").split()
            atom_indices_g2 = st.text_input(
                f"Enter indices (space-separated) for atoms in pair {i + 1} group 2").split()

            try:
                # Convert indices from string to integer
                atom_indices_g1 = [int(index) for index in atom_indices_g1]
                atom_indices_g2 = [int(index) for index in atom_indices_g2]
            except ValueError:
                st.write("Please ensure you've entered only space-separated integers for atom indices.")
                return

            # Create AtomGroup instances

            ag1 = u.atoms[atom_indices_g1]

            ag2 = u.atoms[atom_indices_g2]

            # Append atom group pairs to the list

            group_pairs.append((ag1, ag2))

        if st.button('Do individual tracking analysis'):

            try:

                st.write("Running individual tracking analysis...")

                rdf_data = site_specific_rdf(u, group_pairs, bins=75, range=(min_dist, max_dist), density=True)

                rdf_dataframe = rdf_to_dataframe(rdf_data)

                # Create and display the plot after rdf_df is generated.
                rdf_plot_v2 = plot_atom_pairs_rdf(rdf_dataframe)
                st.plotly_chart(rdf_plot_v2, use_container_width=True)

                # Create and display the download button for the rdf_df data.
                csv_data = rdf_dataframe.to_csv(index=True).encode()
                st.download_button("Download rdf data as CSV", csv_data, file_name="rdf_data.csv", mime="text/csv")


            except Exception as e:

                st.write(f"Error: {str(e)}")

    pass






def handle_distortion_analysis(u, n, A, B):
    outputs = []
    for idx, ts in enumerate(u.trajectory[::n]):
        # logging.info(f"Processing frame {idx}")

        # Convert to ASE Atoms object
        atoms = Atoms(symbols=[atom.element for atom in u.atoms],
                      positions=u.atoms.positions,
                      cell=u.dimensions[:3],
                      pbc=[bool(x) for x in u.dimensions[3:]])

        # Call filter_atoms_by_symbols_and_extend
        new_atoms, periodic_image_dict = filter_atoms_by_symbols_and_extend(atoms, A, B)
        filtered_AB_groups = identify_AB_groups(new_atoms, A, B)
        bond_distance_var = calculate_bond_distance_variance(filtered_AB_groups, new_atoms)

        # Append the output to the results
        outputs.append(bond_distance_var)
    st.write(outputs)

    return outputs

def build_universe_and_analyze(timestep):
    st.write("Building universe...")
    u = build_universe_from_dir('frames_dir', timestep=timestep)
    return u


@st.cache_data(show_spinner="Building MDA universe")
def create_universe(file_buffer_md, timestep):
    with zipfile.ZipFile(file_buffer_md, 'r') as zip_ref:
        zip_ref.extractall('frames_dir')
    timestep = timestep / 1000
    return build_universe_from_dir('frames_dir', timestep=timestep)


previous_file_buffer = None

if MDanalysis_option:
    st.title("Distance Analysis on MD Trajectory")
    timestep = st.number_input("Enter timestep in fs (dt)", min_value=0.0, max_value=5.0, step=0.1)
    file_buffer_md = st.file_uploader("Upload zipped directory", type=["zip"], key="file_buffer_zip")


    if file_buffer_md is not None and timestep is not None:

        # Check if the new file is uploaded, then remove the existing 'frames_dir'
        if file_buffer_md != previous_file_buffer:
            if os.path.exists('frames_dir'):
                shutil.rmtree('frames_dir')
            previous_file_buffer = file_buffer_md


        u = create_universe(file_buffer_md, timestep)

        analysis_type = st.selectbox("Select Analysis Type", ("H-Bond Analysis", "Distance Analysis", "Average Structure", "Distortion Analysis", "Pair Distribution Function"))

        if analysis_type == "H-Bond Analysis":
            handle_h_bond_analysis(u)

        elif analysis_type == "Distance Analysis":
            handle_distance_analysis(u)

        elif analysis_type == "Distortion Analysis":
            n_image = st.number_input("Enter image interval", 100)
            if n_image is not None:
                handle_distortion_analysis(u, n=n_image, A="Pb", B="I")

        elif analysis_type == "Average Structure":
            start_time = st.number_input("Enter time (ps) to set first frame: ", min_value=0.00, max_value=100.0, step=0.0001)

            if start_time is not None and st.button("Generate Average Structure"):
                cif_file = average_structure_to_cif(u, start_time)

                with open(cif_file, "rb") as f:
                    btn = st.download_button(
                        label="Download Average Structure",
                        data=f,
                        file_name="Average_structure.in"
                    )
                os.remove("Average_structure.in")

        elif analysis_type == "Pair Distribution Function":
            handle_rdf_analysis(u)









