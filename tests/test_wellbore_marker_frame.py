import numpy as np
import pandas as pd

import resqpy.well
import resqpy.organize as rqo
import resqpy.olio.uuid as bu
from resqpy.model import Model


def test_from_dataframe_and_dataframe(example_model_and_crs):
    # Test that a WellboreMarkerFrame object can be correctly instantiated from a source dataframe and verify that the
    # dataframe generated by the dataframe() method matches the source dataframe

    # --------- Arrange ----------
    # Create a WellboreMarkerFrame object in memory
    # Load example model from a fixture
    model, crs = example_model_and_crs
    epc_path = model.epc_file

    # Create a trajectory
    well_name = 'Banoffee'
    elevation = 100
    datum = resqpy.well.MdDatum(parent_model = model,
                                crs_uuid = crs.uuid,
                                location = (0, 0, -elevation),
                                md_reference = 'kelly bushing')
    mds = np.array([300.0, 310.0, 330.0])
    zs = mds - elevation
    source_dataframe = pd.DataFrame({
        'MD': mds,
        'X': [150.0, 165.0, 180.0],
        'Y': [240.0, 260.0, 290.0],
        'Z': zs,
    })
    trajectory = resqpy.well.Trajectory(parent_model = model,
                                        data_frame = source_dataframe,
                                        well_name = well_name,
                                        md_datum = datum,
                                        length_uom = 'm')
    trajectory.write_hdf5()
    trajectory.create_xml()
    trajectory_uuid = trajectory.uuid

    # Create features and interpretations
    horizon_feature_1 = rqo.GeneticBoundaryFeature(parent_model = model,
                                                   kind = 'horizon',
                                                   feature_name = 'horizon_feature_1')
    horizon_feature_1.create_xml()
    horizon_interp_1 = rqo.HorizonInterpretation(parent_model = model,
                                                 title = 'horizon_interp_1',
                                                 genetic_boundary_feature = horizon_feature_1,
                                                 sequence_stratigraphy_surface = 'flooding',
                                                 boundary_relation_list = ['conformable'])
    horizon_interp_1.create_xml()

    woc_feature_1 = rqo.FluidBoundaryFeature(parent_model = model, kind = 'water oil contact', feature_name = 'woc_1')
    # fluid boundary feature does not have an associated interpretation
    woc_feature_1.create_xml()

    fault_feature_1 = rqo.TectonicBoundaryFeature(parent_model = model,
                                                  kind = 'fault',
                                                  feature_name = 'fault_feature_1')
    fault_feature_1.create_xml()
    fault_interp_1 = rqo.FaultInterpretation(parent_model = model,
                                             title = 'fault_interp_1',
                                             tectonic_boundary_feature = fault_feature_1,
                                             is_normal = True,
                                             maximum_throw = 15)
    fault_interp_1.create_xml()

    df = pd.DataFrame({
        'MD': [400.0, 410.0, 430.0],
        'Boundary_Feature_Type': ['horizon', 'water oil contact', 'fault'],
        'Marker_Citation_Title': ['marker_horizon_1', 'marker_woc_1', 'marker_fault_1'],
        'Interp_Citation_Title': ['horizon_interp_1', None, 'fault_interp_1'],
    })

    # Create a wellbore marker frame from a dataframe
    wellbore_marker_frame = resqpy.well.WellboreMarkerFrame.from_dataframe(
        parent_model = model,
        dataframe = df,
        trajectory_uuid = trajectory_uuid,
        title = 'WBF1',
        originator = 'Human',
        extra_metadata = {'target_reservoir': 'treacle'})
    # --------- Act ----------
    # Save to disk
    wellbore_marker_frame.write_hdf5()
    wellbore_marker_frame.create_xml()
    wmf_uuid = wellbore_marker_frame.uuid  # called after create_xml method as it can alter the uuid
    # get the uuids of each of the markers
    marker_uuids = []
    for marker in wellbore_marker_frame.marker_list:
        marker_uuids.append(marker.uuid)
    model.store_epc()
    model.h5_release()

    # Clear memory
    del model, wellbore_marker_frame, datum, trajectory

    # Reload from disk
    model2 = Model(epc_file = epc_path)
    wellbore_marker_frame2 = resqpy.well.WellboreMarkerFrame(parent_model = model2, uuid = wmf_uuid)

    # Get the uuids of each of the markers
    marker_uuids2 = []
    for marker in wellbore_marker_frame2.marker_list:
        marker_uuids2.append(marker.uuid)

    # Create a dataframe from the attributes of the new wellbore marker frame object
    df2 = wellbore_marker_frame2.dataframe()
    df2_filtered_cols = df2[['MD', 'Boundary_Feature_Type', 'Marker_Citation_Title', 'Interp_Citation_Title']]

    # --------- Assert ----------
    # test that the attributes were reloaded correctly
    assert bu.matching_uuids(wellbore_marker_frame2.trajectory_uuid, trajectory_uuid)
    assert wellbore_marker_frame2.node_count == len(wellbore_marker_frame2.node_mds) == len(
        wellbore_marker_frame2.marker_list) == 3
    assert wellbore_marker_frame2.title == 'WBF1'
    assert wellbore_marker_frame2.originator == 'Human'
    assert wellbore_marker_frame2.extra_metadata == {'target_reservoir': 'treacle'}
    np.testing.assert_almost_equal(wellbore_marker_frame2.node_mds, np.array([400.0, 410.0, 430.0]))
    for uuid1, uuid2 in zip(marker_uuids, marker_uuids2):
        assert bu.matching_uuids(uuid1, uuid2)
    # test that the generated dataframe contains the same data as the original df
    pd.testing.assert_frame_equal(df, df2_filtered_cols, check_dtype = False)


def test_find_marker_index_from_interp_uuid(example_model_and_crs):

    # --------- Arrange ----------
    # Create a WellboreMarkerFrame object in memory
    # Load example model from a fixture
    model, crs = example_model_and_crs

    # Create a trajectory
    well_name = 'Banoffee'
    elevation = 100
    datum = resqpy.well.MdDatum(parent_model = model,
                                crs_uuid = crs.uuid,
                                location = (0, 0, -elevation),
                                md_reference = 'kelly bushing')
    mds = np.array([300.0, 310.0, 330.0])
    zs = mds - elevation
    source_dataframe = pd.DataFrame({
        'MD': mds,
        'X': [150.0, 165.0, 180.0],
        'Y': [240.0, 260.0, 290.0],
        'Z': zs,
    })
    trajectory = resqpy.well.Trajectory(parent_model = model,
                                        data_frame = source_dataframe,
                                        well_name = well_name,
                                        md_datum = datum,
                                        length_uom = 'm')
    trajectory.write_hdf5()
    trajectory.create_xml()
    trajectory_uuid = trajectory.uuid

    # Create features and interpretations
    horizon_feature_1 = rqo.GeneticBoundaryFeature(parent_model = model,
                                                   kind = 'horizon',
                                                   feature_name = 'horizon_feature_1')
    horizon_feature_1.create_xml()
    horizon_interp_1 = rqo.HorizonInterpretation(parent_model = model,
                                                 title = 'horizon_interp_1',
                                                 genetic_boundary_feature = horizon_feature_1,
                                                 sequence_stratigraphy_surface = 'flooding',
                                                 boundary_relation_list = ['conformable'])
    horizon_interp_1.create_xml()
    horizon_interp_1_uuid = horizon_interp_1.uuid

    woc_feature_1 = rqo.FluidBoundaryFeature(parent_model = model, kind = 'water oil contact', feature_name = 'woc_1')
    # fluid boundary feature does not have an associated interpretation
    woc_feature_1.create_xml()

    fault_feature_1 = rqo.TectonicBoundaryFeature(parent_model = model,
                                                  kind = 'fault',
                                                  feature_name = 'fault_feature_1')
    fault_feature_1.create_xml()
    fault_interp_1 = rqo.FaultInterpretation(parent_model = model,
                                             title = 'fault_interp_1',
                                             tectonic_boundary_feature = fault_feature_1,
                                             is_normal = True,
                                             maximum_throw = 15)
    fault_interp_1.create_xml()

    df = pd.DataFrame({
        'MD': [400.0, 410.0, 430.0],
        'Boundary_Feature_Type': ['horizon', 'water oil contact', 'fault'],
        'Marker_Citation_Title': ['marker_horizon_1', 'marker_woc_1', 'marker_fault_1'],
        'Interp_Citation_Title': ['horizon_interp_1', None, 'fault_interp_1'],
    })

    # Create a wellbore marker frame from a dataframe
    wellbore_marker_frame = resqpy.well.WellboreMarkerFrame.from_dataframe(
        parent_model = model,
        dataframe = df,
        trajectory_uuid = trajectory_uuid,
        title = 'WBF1',
        originator = 'Human',
        extra_metadata = {'target_reservoir': 'treacle'})
    # Create a random uuid that's not related to any interpretation
    random_uuid = bu.new_uuid()
    # --------- Act ----------
    # Find marker indices based on interpretation uuids
    horizon_index = wellbore_marker_frame.find_marker_index_from_interp(interpretation_uuid = horizon_interp_1_uuid)
    random_index = wellbore_marker_frame.find_marker_index_from_interp(interpretation_uuid = random_uuid)

    # --------- Act ----------
    assert horizon_index == 0
    assert random_index is None


def test_find_marker_from_index(example_model_and_crs):
    # --------- Arrange ----------
    # Create a WellboreMarkerFrame object in memory
    # Load example model from a fixture
    model, crs = example_model_and_crs

    # Create a trajectory
    well_name = 'Banoffee'
    elevation = 100
    datum = resqpy.well.MdDatum(parent_model = model,
                                crs_uuid = crs.uuid,
                                location = (0, 0, -elevation),
                                md_reference = 'kelly bushing')
    mds = np.array([300.0, 310.0, 330.0])
    zs = mds - elevation
    source_dataframe = pd.DataFrame({
        'MD': mds,
        'X': [150.0, 165.0, 180.0],
        'Y': [240.0, 260.0, 290.0],
        'Z': zs,
    })
    trajectory = resqpy.well.Trajectory(parent_model = model,
                                        data_frame = source_dataframe,
                                        well_name = well_name,
                                        md_datum = datum,
                                        length_uom = 'm')
    trajectory.write_hdf5()
    trajectory.create_xml()
    trajectory_uuid = trajectory.uuid

    # Create features and interpretations
    horizon_feature_1 = rqo.GeneticBoundaryFeature(parent_model = model,
                                                   kind = 'horizon',
                                                   feature_name = 'horizon_feature_1')
    horizon_feature_1.create_xml()
    horizon_interp_1 = rqo.HorizonInterpretation(parent_model = model,
                                                 title = 'horizon_interp_1',
                                                 genetic_boundary_feature = horizon_feature_1,
                                                 sequence_stratigraphy_surface = 'flooding',
                                                 boundary_relation_list = ['conformable'])
    horizon_interp_1.create_xml()

    woc_feature_1 = rqo.FluidBoundaryFeature(parent_model = model, kind = 'water oil contact', feature_name = 'woc_1')
    # fluid boundary feature does not have an associated interpretation
    woc_feature_1.create_xml()

    fault_feature_1 = rqo.TectonicBoundaryFeature(parent_model = model,
                                                  kind = 'fault',
                                                  feature_name = 'fault_feature_1')
    fault_feature_1.create_xml()
    fault_interp_1 = rqo.FaultInterpretation(parent_model = model,
                                             title = 'fault_interp_1',
                                             tectonic_boundary_feature = fault_feature_1,
                                             is_normal = True,
                                             maximum_throw = 15)
    fault_interp_1.create_xml()

    df = pd.DataFrame({
        'MD': [400.0, 410.0, 430.0],
        'Boundary_Feature_Type': ['horizon', 'water oil contact', 'fault'],
        'Marker_Citation_Title': ['marker_horizon_1', 'marker_woc_1', 'marker_fault_1'],
        'Interp_Citation_Title': ['horizon_interp_1', None, 'fault_interp_1'],
    })

    # Create a wellbore marker frame from a dataframe
    wellbore_marker_frame = resqpy.well.WellboreMarkerFrame.from_dataframe(
        parent_model = model,
        dataframe = df,
        trajectory_uuid = trajectory_uuid,
        title = 'WBF1',
        originator = 'Human',
        extra_metadata = {'target_reservoir': 'treacle'})

    # --------- Act ----------
    # Find marker indices based on interpretation uuids
    found_woc_marker = wellbore_marker_frame.find_marker_from_index(idx = 1)
    index_error_result = wellbore_marker_frame.find_marker_from_index(idx = 5)

    # --------- Assert ----------
    assert bu.matching_uuids(wellbore_marker_frame.marker_list[1].uuid, found_woc_marker.uuid)
    assert index_error_result is None
