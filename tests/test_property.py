import math as maths
import os

import numpy as np
import pytest
from numpy.testing import assert_array_almost_equal

import resqpy.derived_model as rqdm
import resqpy.grid as grr
import resqpy.model as rq
import resqpy.olio.uuid as bu
import resqpy.olio.vector_utilities as vec
import resqpy.property as rqp
import resqpy.time_series as rqts
import resqpy.weights_and_measures as bwam
import resqpy.surface as rqs

# ---- Test PropertyCollection methods ---

# TODO


def test_property(tmp_path):
    epc = os.path.join(tmp_path, 'test_prop.epc')
    model = rq.new_model(epc)
    grid = grr.RegularGrid(model, extent_kji = (2, 3, 4))
    grid.write_hdf5()
    grid.create_xml()
    a1 = np.random.random(grid.extent_kji)
    p1 = rqp.Property.from_array(model,
                                 a1,
                                 source_info = 'random',
                                 keyword = 'NETGRS',
                                 support_uuid = grid.uuid,
                                 property_kind = 'net to gross ratio',
                                 indexable_element = 'cells',
                                 uom = 'm3/m3')
    a3 = np.random.random((grid.nk + 1, grid.nj + 1, grid.ni + 1))
    p3 = rqp.Property.from_array(model,
                                 a3,
                                 source_info = 'random',
                                 keyword = 'jiggle shared nodes',
                                 support_uuid = grid.uuid,
                                 property_kind = 'length',
                                 indexable_element = 'nodes',
                                 uom = 'm3')
    a4 = np.random.random((grid.nk, grid.nj, grid.ni, 2, 2, 2))
    p4 = rqp.Property.from_array(model,
                                 a4,
                                 source_info = 'random',
                                 keyword = 'jiggle nodes per cell',
                                 support_uuid = grid.uuid,
                                 property_kind = 'length',
                                 indexable_element = 'nodes per cell',
                                 uom = 'm3')
    pk = rqp.PropertyKind(model, title = 'facies', parent_property_kind = 'discrete')
    pk.create_xml()
    facies_dict = {0: 'background'}
    for i in range(1, 10):
        facies_dict[i] = 'facies ' + str(i)
    sl = rqp.StringLookup(model, int_to_str_dict = facies_dict, title = 'facies table')
    sl.create_xml()
    shape2 = tuple(list(grid.extent_kji) + [2])
    a2 = (np.random.random(shape2) * 10.0).astype(int)
    p2 = rqp.Property.from_array(model,
                                 a2,
                                 source_info = 'random',
                                 keyword = 'FACIES',
                                 support_uuid = grid.uuid,
                                 local_property_kind_uuid = pk.uuid,
                                 indexable_element = 'cells',
                                 discrete = True,
                                 null_value = 0,
                                 count = 2,
                                 string_lookup_uuid = sl.uuid)
    model.store_epc()
    model = rq.Model(epc)
    ntg_uuid = model.uuid(obj_type = p1.resqml_type, title = 'NETGRS')
    assert ntg_uuid is not None
    p1p = rqp.Property(model, uuid = ntg_uuid)
    assert np.all(p1p.array_ref() == p1.array_ref())
    assert p1p.uom() == 'm3/m3'
    facies_uuid = model.uuid(obj_type = p2.resqml_type, title = 'FACIES')
    assert facies_uuid is not None
    p2p = rqp.Property(model, uuid = facies_uuid)
    assert np.all(p2p.array_ref() == p2.array_ref())
    assert p2p.null_value() is not None and p2p.null_value() == 0
    grid = model.grid()
    jiggle_parts = model.parts(title = 'jiggle', title_mode = 'starts')
    assert len(jiggle_parts) == 2
    jiggle_shared_uuid = model.uuid(parts_list = jiggle_parts, title = 'shared', title_mode = 'contains')
    assert jiggle_shared_uuid is not None
    p3p = rqp.Property(model, uuid = jiggle_shared_uuid)
    assert p3p is not None
    assert p3p.array_ref().shape == (grid.nk + 1, grid.nj + 1, grid.ni + 1)
    jiggle_per_cell_uuid = model.uuid(parts_list = jiggle_parts, title = 'per cell', title_mode = 'ends')
    assert jiggle_per_cell_uuid is not None
    # four properties created here, plus 3 regular grid cell lengths properties
    assert grid.property_collection.number_of_parts() == 7
    collection = rqp.selective_version_of_collection(grid.property_collection,
                                                     property_kind = 'length',
                                                     uuid = jiggle_per_cell_uuid)
    assert collection is not None
    assert collection.number_of_parts() == 1
    p4p = rqp.Property.from_singleton_collection(collection)
    assert p4p is not None
    assert p4p.array_ref().shape == (grid.nk, grid.nj, grid.ni, 2, 2, 2)


def test_create_Property_from_singleton_collection(tmp_model):

    # Arrange
    grid = grr.RegularGrid(tmp_model, extent_kji = (2, 3, 4))
    grid.write_hdf5()
    grid.create_xml(add_cell_length_properties = True)
    collection = rqp.selective_version_of_collection(grid.property_collection,
                                                     property_kind = 'cell length',
                                                     facet_type = 'direction',
                                                     facet = 'J')
    assert collection.number_of_parts() == 1
    # Check property can be created
    prop = rqp.Property.from_singleton_collection(collection)
    assert np.all(np.isclose(prop.array_ref(), 1.0))


# ---- Test property kind parsing ---


def test_property_kinds():
    prop_kinds = bwam.valid_property_kinds()
    assert "angle per time" in prop_kinds
    assert "foobar" not in prop_kinds


# ---- Test infer_property_kind ---


@pytest.mark.parametrize(
    "input_name, input_unit, kind, facet_type, facet",
    [
        ('gamma ray API unit', 'gAPI', 'gamma ray API unit', None, None),  # Just a placeholder for now
        ('', '', 'Unknown', None, None),  # What should default return?
    ])
def test_infer_property_kind(input_name, input_unit, kind, facet_type, facet):
    kind_, facet_type_, facet_ = rqp.infer_property_kind(input_name, input_unit)
    assert kind == kind_
    assert facet_type == facet_type_
    assert facet == facet_


def test_bespoke_property_kind():
    model = rq.Model(create_basics = True)
    em = {'something': 'important', 'and_another_thing': 42}
    pk1 = rqp.PropertyKind(model, title = 'my kind of property', extra_metadata = em)
    pk1.create_xml()
    assert len(model.uuids(obj_type = 'PropertyKind')) == 1
    pk2 = rqp.PropertyKind(model, title = 'my kind of property', extra_metadata = em)
    pk2.create_xml()
    assert len(model.uuids(obj_type = 'PropertyKind')) == 1
    pk3 = rqp.PropertyKind(model, title = 'your kind of property', extra_metadata = em)
    pk3.create_xml()
    assert len(model.uuids(obj_type = 'PropertyKind')) == 2
    pk4 = rqp.PropertyKind(model, title = 'my kind of property')
    pk4.create_xml()
    assert len(model.uuids(obj_type = 'PropertyKind')) == 3
    pk5 = rqp.PropertyKind(model, title = 'my kind of property', parent_property_kind = 'discrete', extra_metadata = em)
    pk5.create_xml()
    assert len(model.uuids(obj_type = 'PropertyKind')) == 4
    pk6 = rqp.PropertyKind(model, title = 'my kind of property', parent_property_kind = 'continuous')
    pk6.create_xml()
    assert len(model.uuids(obj_type = 'PropertyKind')) == 4
    assert pk6 == pk4


def test_string_lookup():
    model = rq.Model(create_basics = True)
    d = {1: 'peaty', 2: 'muddy', 3: 'sandy', 4: 'granite'}
    sl = rqp.StringLookup(model, int_to_str_dict = d, title = 'stargazing')
    sl.create_xml()
    assert sl.length() == 5 if sl.stored_as_list else 4
    assert sl.get_string(3) == 'sandy'
    assert sl.get_index_for_string('muddy') == 2
    d2 = {0: 'nothing', 27: 'something', 173: 'amazing', 1072: 'brilliant'}
    sl2 = rqp.StringLookup(model, int_to_str_dict = d2, title = 'head in the clouds')
    assert not sl2.stored_as_list
    assert sl2.length() == 4
    assert sl2.get_string(1072) == 'brilliant'
    assert sl2.get_string(555) is None
    assert sl2.get_index_for_string('amazing') == 173
    sl2.create_xml()
    assert set(model.titles(obj_type = 'StringTableLookup')) == set(['stargazing', 'head in the clouds'])
    assert sl != sl2


def test_constant_array_expansion(tmp_path):
    epc = os.path.join(tmp_path, 'boring.epc')
    model = rq.new_model(epc)
    grid = grr.RegularGrid(model, extent_kji = (2, 3, 4))
    grid.write_hdf5()
    grid.create_xml()
    p1 = rqp.Property.from_array(model,
                                 cached_array = None,
                                 source_info = 'test',
                                 keyword = 'constant pi',
                                 support_uuid = grid.uuid,
                                 property_kind = 'continuous',
                                 indexable_element = 'cells',
                                 const_value = maths.pi,
                                 expand_const_arrays = True)
    p2 = rqp.Property.from_array(model,
                                 cached_array = None,
                                 source_info = 'test',
                                 keyword = 'constant three',
                                 support_uuid = grid.uuid,
                                 property_kind = 'discrete',
                                 discrete = True,
                                 indexable_element = 'cells',
                                 const_value = 3,
                                 expand_const_arrays = False)
    model.store_epc()
    # re-open the model and check that p1 appears as an ordinary array whilst p2 is still a constant
    model = rq.Model(epc)
    p1p = rqp.Property(model, uuid = p1.uuid)
    p2p = rqp.Property(model, uuid = p2.uuid)
    assert p1p.constant_value() is None
    assert p2p.constant_value() == 3
    assert_array_almost_equal(p1p.array_ref(), np.full(grid.extent_kji, maths.pi))
    assert np.all(p2p.array_ref() == 3) and p2p.array_ref().shape == tuple(grid.extent_kji)


def test_property_extra_metadata(tmp_path):
    # set up test model with a grid
    epc = os.path.join(tmp_path, 'em_test.epc')
    model = rq.new_model(epc)
    grid = grr.RegularGrid(model, extent_kji = (2, 3, 4))
    grid.write_hdf5()
    grid.create_xml()
    model.store_epc()
    # add a grid property with some extra metadata
    a = np.arange(24).astype(float).reshape((2, 3, 4))
    em = {'important': 'something', 'also': 'nothing'}
    uuid = rqdm.add_one_grid_property_array(epc, a, 'length', title = 'nonsense', uom = 'm', extra_metadata = em)
    # re-open the model and check that extra metadata has been preserved
    model = rq.Model(epc)
    p = rqp.Property(model, uuid = uuid)
    for item in em.items():
        assert item in p.extra_metadata.items()


def test_points_properties(tmp_path):

    epc = os.path.join(tmp_path, 'points_test.epc')
    model = rq.new_model(epc)

    extent_kji = (2, 3, 4)
    ensemble_size = 5
    faulted_ensemble_size = 2
    time_series_size = 6

    # create a geological time series
    years = [int(t) for t in np.linspace(-252170000, -66000000, num = time_series_size, dtype = int)]
    ts = rqts.GeologicTimeSeries.from_year_list(model, year_list = years, title = 'Mesozoic time series')
    ts.create_xml()
    ts_uuid = ts.uuid
    assert ts.timeframe == 'geologic'

    # create a simple grid without an explicit geometry and ensure it has a property collection initialised
    grid = grr.RegularGrid(model,
                           extent_kji = extent_kji,
                           origin = (0.0, 0.0, 1000.0),
                           dxyz = (100.0, 100.0, -10.0),
                           title = 'unfaulted grid')
    # patch K direction, even though it won't be stored in xml
    grid.k_direction_is_down = False
    grid.grid_is_right_handed = not grid.grid_is_right_handed
    # generate xml and establish a property collection for the grid
    grid.create_xml()
    if grid.property_collection is None:
        grid.property_collection = rqp.PropertyCollection(support = grid)
    pc = grid.property_collection

    # shape of points property arrays
    points_shape = tuple(list(extent_kji) + [3])

    # create a static points property with multiple realisations
    for r in range(ensemble_size):
        stress = vec.unit_vectors(np.random.random(points_shape) + 0.1)
        pc.add_cached_array_to_imported_list(stress,
                                             'random stress vectors',
                                             'stress direction',
                                             uom = 'm',
                                             property_kind = 'length',
                                             realization = r,
                                             indexable_element = 'cells',
                                             points = True)
    pc.write_hdf5_for_imported_list()
    pc.create_xml_for_imported_list_and_add_parts_to_model()

    # create a dynamic points property (indexable cells) related to the geological time series
    for r in range(ensemble_size):
        centres = grid.centre_point().copy()
        for time_index in range(time_series_size):
            pc.add_cached_array_to_imported_list(centres,
                                                 'dynamic cell centres',
                                                 'centres',
                                                 uom = 'm',
                                                 property_kind = 'length',
                                                 realization = r,
                                                 time_index = time_index,
                                                 indexable_element = 'cells',
                                                 points = True)
            centres[..., 2] += 100.0 * (r + 1)
    pc.write_hdf5_for_imported_list()
    pc.create_xml_for_imported_list_and_add_parts_to_model(time_series_uuid = ts_uuid)

    # create a dynamic points property (indexable nodes) related to the geological time series
    # also create a parallel set of active cell properties
    for r in range(ensemble_size):
        nodes = grid.points_ref().copy()
        for time_index in range(time_series_size):
            pc.add_cached_array_to_imported_list(nodes,
                                                 'dynamic nodes',
                                                 'points',
                                                 uom = 'm',
                                                 property_kind = 'length',
                                                 realization = r,
                                                 time_index = time_index,
                                                 indexable_element = 'nodes',
                                                 points = True)
            nodes[..., 2] += 100.0 * (r + 1)
            active_array = np.ones(extent_kji, dtype = bool)
            # de-activate some cells
            if extent_kji[0] > 1 and time_index < time_series_size // 2:
                active_array[extent_kji[0] // 2:] = False
            if extent_kji[2] > 1:
                active_array[:, :, r % extent_kji[2]] = False
            rqp.write_hdf5_and_create_xml_for_active_property(model,
                                                              active_array,
                                                              grid.uuid,
                                                              title = 'ACTIVE',
                                                              realization = r,
                                                              time_series_uuid = ts_uuid,
                                                              time_index = time_index)
    pc.write_hdf5_for_imported_list()
    pc.create_xml_for_imported_list_and_add_parts_to_model(time_series_uuid = ts_uuid)

    # store the xml
    model.store_epc()

    # create a second grid being a copy of the first grid but with a fault
    fault_pillar_dict = {'the fault': [(2, 0), (2, 1), (2, 2), (1, 2), (1, 3), (1, 4)]}
    rqdm.add_faults(epc, source_grid = grid, full_pillar_list_dict = fault_pillar_dict, new_grid_title = 'faulted grid')

    # re-open the model and build a dynamic points property for the faulted grid
    # NB. this test implicitly has the oldest geometry as the 'official' grid geometry whereas
    # the RESQML documentation states that the geometry stored for the grid should be 'current' (ie. youngest)
    model = rq.Model(epc)
    f_grid = model.grid(title = 'faulted grid')
    assert f_grid is not None
    pc = f_grid.property_collection
    for r in range(faulted_ensemble_size):
        nodes = f_grid.points_ref().copy()
        for time_index in range(time_series_size):
            pc.add_cached_array_to_imported_list(nodes,
                                                 'faulted dynamic nodes',
                                                 'faulted points',
                                                 uom = 'm',
                                                 property_kind = 'length',
                                                 realization = r,
                                                 time_index = time_index,
                                                 indexable_element = 'nodes',
                                                 points = True)
            nodes[..., 2] += 101.0 * (r + 1)  # add more and more depth for each realisation
    pc.write_hdf5_for_imported_list()
    pc.create_xml_for_imported_list_and_add_parts_to_model(time_series_uuid = ts_uuid)

    # store the xml again
    model.store_epc()

    # re-open the model and access the grid properties
    model = rq.Model(epc)
    grid = model.grid(title = 'unfaulted grid')
    pc = grid.property_collection

    # check that the grid as stored has all cells active
    assert grid.inactive is None or np.count_nonzero(grid.inactive) == 0

    # load a static points property for a single realisation
    sample_stress_part = pc.singleton(realization = ensemble_size // 2,
                                      citation_title = 'stress direction',
                                      points = True)
    assert sample_stress_part is not None
    sample_stress = pc.single_array_ref(realization = ensemble_size // 2,
                                        citation_title = 'stress direction',
                                        points = True)
    assert sample_stress is not None and sample_stress.ndim == 4
    assert np.all(sample_stress.shape[:3] == extent_kji)
    assert sample_stress.shape[3] == 3
    assert np.count_nonzero(np.isnan(sample_stress)) == 0
    stress_uuid = pc.uuid_for_part(sample_stress_part)

    # load the same property using the Property class
    stress_p = rqp.Property(model, uuid = stress_uuid)
    assert stress_p is not None
    assert stress_p.is_points()
    sample_stress = stress_p.array_ref()
    assert sample_stress is not None and sample_stress.ndim == 4

    # select the dynamic points properties related to the geological time series and indexable by cells
    cc = rqp.selective_version_of_collection(grid.property_collection,
                                             indexable = 'cells',
                                             points = True,
                                             time_series_uuid = ts_uuid)
    assert cc.number_of_parts() == ensemble_size * time_series_size

    # check that 5 dimensional numpy arrays can be set up, each covering time indices for a single realisation
    for r in range(ensemble_size):
        rcc = rqp.selective_version_of_collection(cc, realization = r)
        assert rcc.number_of_parts() == time_series_size
        dynamic_nodes = rcc.time_series_array_ref()
        assert dynamic_nodes.ndim == 5
        assert dynamic_nodes.shape[0] == time_series_size
        assert np.all(dynamic_nodes.shape[1:4] == np.array(extent_kji))
        assert dynamic_nodes.shape[-1] == 3
        mean_depth = np.nanmean(dynamic_nodes[..., 2])
        assert mean_depth > 1000.0

    # select the dynamic points properties related to the geological time series and indexable by nodes
    nc = rqp.selective_version_of_collection(grid.property_collection,
                                             indexable = 'nodes',
                                             points = True,
                                             time_series_uuid = ts_uuid)
    assert nc.number_of_parts() == ensemble_size * time_series_size

    # check that the cached points for the grid can be populated from a points property
    grid.make_regular_points_cached()
    r = ensemble_size // 2
    ti = time_series_size // 2
    a = nc.single_array_ref(realization = r, time_index = ti)
    grid.set_cached_points_from_property(property_collection = nc,
                                         realization = r,
                                         time_index = ti,
                                         set_inactive = True,
                                         active_collection = grid.property_collection)
    assert_array_almost_equal(grid.points_cached, nc.single_array_ref(realization = r, time_index = ti))
    # check that grid's time index has been set
    assert grid.time_index == ti
    assert bu.matching_uuids(grid.time_series_uuid, ts_uuid)
    # and that the inactive array now indicates some cells are inactive
    assert grid.inactive is not None and np.count_nonzero(grid.inactive) > 0

    # check that 5 dimensional numpy arrays can be set up, each covering realisations for a single time index
    for ti in range(time_series_size):
        tnc = rqp.selective_version_of_collection(nc, time_index = ti)
        assert tnc.number_of_parts() == ensemble_size
        dynamic_nodes = tnc.realizations_array_ref()
        assert dynamic_nodes.ndim == 5
        assert dynamic_nodes.shape[0] == ensemble_size
        assert np.all(dynamic_nodes.shape[1:4] == np.array(extent_kji) + 1)
        assert dynamic_nodes.shape[-1] == 3
        mean_depth = np.nanmean(dynamic_nodes[..., 2])
        assert mean_depth > 1000.0

    # check the faulted grid properties
    f_grid = model.grid(title = 'faulted grid')
    assert f_grid is not None
    assert not f_grid.k_direction_is_down
    f_grid.set_k_direction_from_points()
    assert not f_grid.k_direction_is_down

    # compute and cache cell centre points
    older_centres = f_grid.centre_point()
    assert hasattr(f_grid, 'array_centre_point') and f_grid.array_centre_point is not None

    # select the dynamic points properties related to the geological time series and indexable by nodes
    fnc = rqp.selective_version_of_collection(f_grid.property_collection,
                                              indexable = 'nodes',
                                              points = True,
                                              time_series_uuid = ts_uuid)
    assert fnc.number_of_parts() == faulted_ensemble_size * time_series_size

    # check that the cached points for the faulted grid can be populated from a points property
    r = faulted_ensemble_size // 2
    ti = time_series_size - 1
    p_uuid = fnc.uuid_for_part(fnc.singleton(realization = r, time_index = ti))
    assert p_uuid is not None
    f_grid.set_cached_points_from_property(points_property_uuid = p_uuid,
                                           set_grid_time_index = True,
                                           set_inactive = False)
    assert_array_almost_equal(f_grid.points_cached, fnc.single_array_ref(realization = r, time_index = ti))

    # check that grid's time index has been set
    assert f_grid.time_index == ti
    assert bu.matching_uuids(f_grid.time_series_uuid, ts_uuid)
    # and that the centre point cache has been invalidated
    assert not hasattr(f_grid, 'array_centre_point') or f_grid.array_centre_point is None

    # re-compute centre points based on the dynamically loaded geometry
    younger_centres = f_grid.centre_point()
    assert hasattr(f_grid, 'array_centre_point') and f_grid.array_centre_point is not None

    # check that later centres are vertically below the earlier centres
    # (in this example, the depths of all cells are increasing with time)
    assert_array_almost_equal(older_centres[..., :2], younger_centres[..., :2])  # xy
    assert np.all(older_centres[..., 2] < younger_centres[..., 2])  # depths


def test_remove_part_from_dict(example_model_with_properties):
    # Arrange
    model = example_model_with_properties
    pc = model.grid().property_collection
    assert pc is not None
    assert len(pc.parts()) == 8
    part = pc.parts()[0]

    # Act
    pc.remove_part_from_dict(part)

    # Assert
    assert len(pc.parts()) == 7
    assert part not in pc.parts()


def test_part_str(example_model_with_prop_ts_rels):
    # Arrange
    model = example_model_with_prop_ts_rels
    pc = model.grid().property_collection
    assert pc is not None
    part_disc = pc.parts()[0]
    part_cont = pc.parts()[-1]
    part_facet = pc.parts()[4]

    # Act / Assert
    assert pc.part_str(part_disc) == 'discrete (Zone)'
    assert pc.part_str(part_disc, include_citation_title = False) == 'discrete'
    assert pc.part_str(part_cont) == 'saturation: water; timestep: 2 (SW)'
    assert pc.part_str(part_cont, include_citation_title = False) == 'saturation: water; timestep: 2'
    assert pc.part_str(part_facet) == 'rock permeability: J (Perm)'
    assert pc.part_str(part_facet, include_citation_title = False) == 'rock permeability: J'


def test_part_filename(example_model_with_prop_ts_rels):
    # Arrange
    model = example_model_with_prop_ts_rels
    pc = model.grid().property_collection
    assert pc is not None
    part_disc = pc.parts()[0]
    part_cont = pc.parts()[-1]
    part_facet = pc.parts()[4]

    # Act / Assert
    assert pc.part_filename(part_disc) == 'discrete'
    assert pc.part_filename(part_cont) == 'saturation_water_ts_2'
    assert pc.part_filename(part_facet) == 'rock_permeability_J'


def test_grid_for_part(example_model_with_properties):
    # Arrange
    model = example_model_with_properties
    pc = model.grid().property_collection
    assert pc is not None
    part = pc.parts()[0]

    # Act
    grid = pc.grid_for_part(part)

    # Assert
    assert grid == model.grid()


def test_all_discrete(example_model_with_properties):
    # Arrange
    model = example_model_with_properties
    pc = model.grid().property_collection
    assert pc is not None

    # Act / Assert
    assert not pc.all_discrete()

    # Arrange
    for part in pc.parts():
        if pc.continuous_for_part(part):
            pc.remove_part_from_dict(part)

    # Act / Assert
    assert len(pc.parts()) == 4
    assert pc.all_discrete()


def test_h5_slice(example_model_with_properties):
    # Arrange
    model = example_model_with_properties
    pc = model.grid().property_collection
    assert pc is not None

    # Act  / Assert
    part = pc.parts()[0]
    full = pc.cached_part_array_ref(part)

    slice = pc.h5_slice(part, (0, 0))
    assert_array_almost_equal(slice, full[0, 0])

    slice = pc.h5_slice(part, (-1, -1))
    assert_array_almost_equal(slice, full[-1, -1])


def test_h5_overwrite_slice(example_model_with_properties):
    # Arrange
    model = example_model_with_properties
    pc = model.grid().property_collection
    assert pc is not None
    part = pc.parts()[0]

    # Act
    slice = pc.h5_slice(part, (0, 0))
    new_slice = np.zeros(shape = slice.shape)
    pc.h5_overwrite_slice(part, array_slice = new_slice, slice_tuple = (0, 0))

    # Assert
    new_full = pc.cached_part_array_ref(part)
    assert_array_almost_equal(new_slice, new_full[0, 0])


def test_string_lookup_for_part(example_model_with_prop_ts_rels):
    # Arrange
    model = example_model_with_prop_ts_rels
    pc = model.grid().property_collection
    lookup = model.parts_list_of_type('obj_StringTableLookup')[0]
    assert lookup is not None
    facies_part = [part for part in pc.parts() if pc.citation_title_for_part(part) == 'Facies']
    assert len(facies_part) == 1

    # Act
    lookup_uuid = pc.string_lookup_uuid_for_part(facies_part[0])

    # Assert
    assert bu.matching_uuids(lookup_uuid, model.uuid_for_part(lookup))


def test_establish_has_multiple_realisations(example_model_with_prop_ts_rels):
    # Arrange
    model = example_model_with_prop_ts_rels
    pc = model.grid().property_collection
    # Assert initial model has multiple
    assert pc.establish_has_multiple_realizations()
    assert pc.has_multiple_realizations()
    # Remove parts with realiations
    for part in pc.parts():
        if pc.realization_for_part(part) is not None:
            pc.remove_part_from_dict(part)
    # Assert new model has not got multiple
    assert len(pc.parts()) == 8
    assert not pc.establish_has_multiple_realizations()
    assert not pc.has_multiple_realizations()


def test_establish_has_multiple_realisations_single(example_model_with_prop_ts_rels):
    # Arrange
    model = example_model_with_prop_ts_rels
    pc = model.grid().property_collection
    # Remove parts with realiation is None or 0
    for part in pc.parts():
        if pc.realization_for_part(part) in [None, 0]:
            pc.remove_part_from_dict(part)
    # Assert new model has not got multiple
    assert len(pc.parts()) == 2
    assert not pc.establish_has_multiple_realizations()
    assert not pc.has_multiple_realizations()


def test_establish_time_set_kind(example_model_with_prop_ts_rels):
    # Arrange
    model = example_model_with_prop_ts_rels
    pc = model.grid().property_collection
    # Assert model is not a time set
    assert pc.establish_time_set_kind() == 'not a time set'

    # Remove parts where ts != 2000-01-01Z
    for part in pc.parts():
        if pc.time_index_for_part(part) != 0:
            pc.remove_part_from_dict(part)
    # Assert new model is a single time
    assert len(pc.parts()) == 1
    assert pc.establish_time_set_kind() == 'single time'


@pytest.mark.skip(reason = 'expected to fail currently')
def test_discombobulated_combobulated_face_arrays(example_model_with_properties):
    # Arrange
    model = example_model_with_properties
    orig = np.array([[[[1, 2, 3, 4, 5, 6], [1, 2, 3, 4, 5, 6]]]])
    pc = model.grid().property_collection

    # Act
    combob = pc.combobulated_face_array(orig)
    assert combob.shape[-1] == 2
    assert combob.shape[-2] == 3
    discombob = pc.discombobulated_face_array(combob)
    assert discombob.shape[-1] == 6

    # Assert
    assert_array_almost_equal(orig, discombob)


def test_time_series_array_ref(example_model_with_prop_ts_rels):
    # Arrange
    model = example_model_with_prop_ts_rels
    pc = model.grid().property_collection
    # Trim the model to only contain properties with timesteps
    for part in pc.parts():
        if pc.time_index_for_part(part) is None:
            pc.remove_part_from_dict(part)
    # Make sure the number of properties is as expected, and they are all the same property
    assert len(pc.parts()) == 3
    assert len(set([pc.citation_title_for_part(part) for part in pc.parts()])) == 1
    # Pull out the full arrays to generate the expected output
    sw1, sw2, sw3 = [pc.cached_part_array_ref(part) for part in pc.parts()]
    expected = np.array([sw1, sw2, sw3])

    # Act
    output = pc.time_series_array_ref()

    # Assert
    assert_array_almost_equal(expected, output)


def test_inherit_parts_from_other_collection(example_model_with_prop_ts_rels):
    # Arrange
    copy_from = example_model_with_prop_ts_rels
    pc_from = copy_from.grid().property_collection

    pc_to = rqp.PropertyCollection()
    pc_to.set_support(model = copy_from, support_uuid = copy_from.grid().uuid)

    orig_from = len(pc_from.parts())

    # Act
    pc_to.inherit_parts_from_other_collection(pc_from)
    # Assert
    assert len(pc_to.parts()) == orig_from


def test_similar_parts_for_time_series_from_other_collection(example_model_with_prop_ts_rels):
    # Arrange
    copy_from = example_model_with_prop_ts_rels
    pc_from = copy_from.grid().property_collection

    pc_to = rqp.PropertyCollection()
    pc_to.set_support(model = copy_from, support_uuid = copy_from.grid().uuid)

    sw_parts = [part for part in pc_from.parts() if pc_from.citation_title_for_part(part) == 'SW']
    example_part = sw_parts[0]

    # Act
    pc_to.inherit_similar_parts_for_time_series_from_other_collection(other = pc_from, example_part = example_part)
    # Assert
    assert len(pc_to.parts()) == len(sw_parts)


def test_similar_parts_for_realizations_from_other_collection(example_model_with_prop_ts_rels):
    # Arrange
    copy_from = example_model_with_prop_ts_rels
    pc_from = copy_from.grid().property_collection

    pc_to = rqp.PropertyCollection(realization = 1)
    pc_to.set_support(model = copy_from)

    rel1_parts = [part for part in pc_from.parts() if pc_from.realization_for_part(part) == 1]
    example_part = rel1_parts[0]

    # Act
    pc_to.inherit_similar_parts_for_realizations_from_other_collection(other = pc_from, example_part = example_part)
    # Assert
    assert len(pc_to.parts()) == len(rel1_parts)


@pytest.mark.skip(reason = 'expected to fail currently')
def test_property_over_time_series_from_collection(example_model_with_prop_ts_rels):
    # Arrange
    model = example_model_with_prop_ts_rels
    pc = model.grid().property_collection

    sw_parts = [part for part in pc.parts() if pc.citation_title_for_part(part) == 'SW']
    example_part = sw_parts[0]

    # Act
    new_pc = rqp.property_over_time_series_from_collection(collection = pc, example_part = example_part)
    # Assert
    assert len(new_pc.parts()) == len(sw_parts)


def test_property_for_keword_from_collection(example_model_with_prop_ts_rels):
    # Arrange
    model = example_model_with_prop_ts_rels
    pc = model.grid().property_collection

    sw_parts = [part for part in pc.parts() if pc.citation_title_for_part(part) == 'SW']

    # Act
    new_pc = rqp.property_collection_for_keyword(collection = pc, keyword = 'sw')
    # Assert
    assert len(new_pc.parts()) == len(sw_parts)


def test_stringlookup_add_str(example_model_and_crs):
    # Arrange
    model, _ = example_model_and_crs
    lookup = rqp.StringLookup(parent_model = model)
    assert lookup.str_dict == {}
    # Act
    lookup.set_string(0, 'channel')
    # Assert
    assert lookup.str_dict == {0: 'channel'}


def test_create_property_set_xml(example_model_with_properties):
    # Arrange
    model = example_model_with_properties
    pc = model.grid().property_collection
    num_parts = len(pc.parts())

    # Act
    pc.create_property_set_xml('Grid property collection')
    model.store_epc()
    reload = rq.Model(model.epc_file)
    # Assert
    assert len(reload.parts_list_of_type('obj_PropertySet')) == 1

    # Act
    prop_set_root = reload.root_for_part(reload.parts_list_of_type('obj_PropertySet')[0])
    pset = rqp.PropertyCollection()
    pset.set_support(support = model.grid())
    pset.populate_from_property_set(prop_set_root)
    # Assert
    assert len(pset.parts()) == num_parts


@pytest.mark.skip(reason = 'expected to fail currently')
def test_override_min_max(example_model_with_properties):
    # Arrange
    model = example_model_with_properties
    pc = model.grid().property_collection
    part = pc.parts()[0]

    print(pc.dict[part])
    vmin = pc.minimum_value_for_part(part)
    vmax = pc.maximum_value_for_part(part)

    # Act
    pc.override_min_max(part, min_value = vmin - 1, max_value = vmax + 1)
    # Assert
    assert pc.minimum_value_for_part(part) == vmin - 1
    assert pc.maximum_value_for_part(part) == vmax + 1


def test_set_support_mesh(example_model_and_crs):
    # Arrange
    model, crs = example_model_and_crs

    ni = 5
    nj = 5
    origin = (0, 0, 0)
    di = dj = 50.0

    # make a regular mesh representation
    support = rqs.Mesh(model,
                       crs_uuid = crs.uuid,
                       mesh_flavour = 'regular',
                       ni = ni,
                       nj = nj,
                       origin = origin,
                       dxyz_dij = np.array([[di, 0.0, 0.0], [0.0, dj, 0.0]]),
                       title = 'regular mesh',
                       originator = 'Emma',
                       extra_metadata = {'testing mode': 'automated'})
    assert support is not None
    support.write_hdf5()
    support.create_xml()

    pc = rqp.PropertyCollection()
    pc.set_support(support = support)


array1 = np.array([[[0, 1, 0, 1, 0], [1, 0, 1, 0, 1], [0, 1, 0, 1, 0], [1, 0, 1, 0, 1], [0, 1, 0, 1, 0]],
                   [[0, 1, 0, 1, 0.], [1, 0, 1, 0, 1], [0, 1, 0, 1, 0], [1, 0, 1, 0, 1], [0, 1, 0, 1, 0]],
                   [[0, 1, 0, 1, 0], [1, 0, 1, 0, 1], [0, 1, 0, 1, 0], [1, 0, 1, 0, 1], [0, 1, 0, 1, 0]]])

array2 = np.where(array1 == 0, 0.5, array1)
array3 = np.array([[[1, 10, 10, 100, 100], [1, 10, 10, 100, 100], [1, 10, 10, 100, 100], [1, 10, 10, 100, 100],
                    [1, 10, 10, 100, 100]],
                   [[1, 10, 10, 100, 100], [1, 10, 10, 100, 100], [1, 10, 10, 100, 100], [1, 10, 10, 100, 100],
                    [1, 10, 10, 100, 100]],
                   [[1, 10, 10, 100, 100], [1, 10, 10, 100, 100], [1, 10, 10, 100, 100], [1, 10, 10, 100, 100],
                    [1, 10, 10, 100, 100]]])
array4 = np.where(array3 == 1, 0, array3)
array4 = np.where(array4 == 100, 1, array4)
array4 = np.where(array4 == 10, 0.090909, array4)
array5 = np.where(array3 == 1, 0, array3)
array5 = np.where(array5 == 100, 1, array5)
array5 = np.where(array5 == 10, 0.5, array5)
array6 = np.where(array3 == 100, np.nan, array3)
array6 = np.where(array6 == 1, 0, array6)
array6 = np.where(array6 == 10, 1, array6)


@pytest.mark.parametrize(
    'name,masked,log,discrete,trust,fix,array,emin,emax',
    [
        ('NTG', False, False, None, False, None, array1, 0, 0.5),  # Simple don't trust minmax
        ('NTG', False, False, None, True, None, array1, 0, 0.5),  # Simple trust minmax
        ('NTG', False, False, None, False, 0.5, array2, -0.5, 0.5),  # Fix 0 at 0.5
        ('Perm', False, False, None, False, None, array4, 1, 100),
        ('Perm', False, True, None, False, None, array5, 0, 2)
    ])  # Logarithmic
def test_norm_array_ref(example_model_with_properties, name, masked, log, discrete, trust, fix, array, emin, emax):
    # Arrange
    model = example_model_with_properties
    pc = model.grid().property_collection
    cont = [part for part in pc.parts() if pc.citation_title_for_part(part) == name][0]

    # Act
    normed, vmin, vmax = pc.normalized_part_array(cont,
                                                  masked = masked,
                                                  use_logarithm = log,
                                                  discrete_cycle = discrete,
                                                  trust_min_max = trust,
                                                  fix_zero_at = fix)

    # Assert
    assert vmin == emin
    assert vmax == emax
    assert_array_almost_equal(normed, array)


def test_norm_array_ref_mask(example_model_with_properties):
    # Arrange
    model = example_model_with_properties
    grid = model.grid()
    # Set up a mask in the grid
    minimask = np.array([0, 0, 0, 1, 1])
    layermask = np.array([minimask] * 5)
    mask = np.array([layermask, layermask, layermask], dtype = 'bool')
    grid.inactive = mask
    pc = model.grid().property_collection
    cont = [part for part in pc.parts() if pc.citation_title_for_part(part) == 'Perm'][0]
    # Act
    normed, vmin, vmax = pc.normalized_part_array(cont, masked = True, use_logarithm = False)
    # Assert
    assert vmin == 1
    assert vmax == 10
    assert_array_almost_equal(array6, normed)


def test_normalized_part_array_discrete(example_model_with_properties):
    # Arrange
    model = example_model_with_properties
    pc = model.grid().property_collection
    disc = [part for part in pc.parts() if pc.citation_title_for_part(part) == 'Zone'][0]
    print(pc.cached_part_array_ref(disc))
    # Act
    normed, vmin, vmax = pc.normalized_part_array(disc, discrete_cycle = 3)
    # Assert
    assert vmin == 0
    assert vmax == 2
    assert normed[0, 0, 0] == 0.5
    assert normed[1, 0, 0] == 1
    assert normed[2, 0, 0] == 0
