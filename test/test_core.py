import unittest
import dedupe
import numpy
import random
import multiprocessing

class RandomPairsTest(unittest.TestCase) :
  def test_random_pair(self) :
    random.seed(123)
    self.assertRaises(ValueError, dedupe.core.randomPairs, 1, 10)
    assert dedupe.core.randomPairs(10, 10).any()
    assert dedupe.core.randomPairs(10*1000000000, 10).any()
    assert numpy.array_equal(dedupe.core.randomPairs(10, 5), 
                             numpy.array([[ 1,  8],
                                          [ 5,  7],
                                          [ 1,  2],
                                          [ 3,  7],
                                          [ 2,  9]]))



class ScoreDuplicates(unittest.TestCase):
  def setUp(self) :
    random.seed(123)

    self.records = iter([(('1', {'name': 'Margret', 'age': '32'}), 
                          ('2', {'name': 'Marga', 'age': '33'})), 
                         (('2', {'name': 'Marga', 'age': '33'}), 
                          ('3', {'name': 'Maria', 'age': '19'})), 
                         (('4', {'name': 'Maria', 'age': '19'}), 
                          ('5', {'name': 'Monica', 'age': '39'})), 
                         (('6', {'name': 'Monica', 'age': '39'}), 
                          ('7', {'name': 'Mira', 'age': '47'})),
                         (('8', {'name': 'Mira', 'age': '47'}), 
                          ('9', {'name': 'Mona', 'age': '9'})),
                        ])

    self.data_model = dedupe.Dedupe({"name" : {'type' : 'String'}}, ()).data_model
    self.data_model['fields']['name']['weight'] = -1.0302742719650269
    self.data_model['bias'] = 4.76

    score_dtype = [('pairs', 'S4', 2), ('score', 'f4', 1)]

    self.desired_scored_pairs = numpy.array([(('1', '2'), 0.96), 
                                             (['2', '3'], 0.96), 
                                             (['4', '5'], 0.78), 
                                             (['6', '7'], 0.72), 
                                             (['8', '9'], 0.84)], 
                                            dtype=score_dtype)



  def test_score_duplicates(self):
    scores = dedupe.core.scoreDuplicates(self.records,
                                         self.data_model,
                                         multiprocessing.Pool(processes=1))

    numpy.testing.assert_equal(scores['pairs'], 
                               self.desired_scored_pairs['pairs'])
    
    numpy.testing.assert_allclose(scores['score'], 
                                  self.desired_scored_pairs['score'], 2)



class FieldDistances(unittest.TestCase):
  def test_field_distance_simple(self) :
    fieldDistances = dedupe.core.fieldDistances
    deduper = dedupe.Dedupe({'name' : {'type' :'String'},
                             'source' : {'type' : 'Source',
                                         'Source Names' : ['a', 'b']}}, [])

    record_pairs = (({'name' : 'steve', 'source' : 'a'}, 
                     {'name' : 'steven', 'source' : 'a'}),)


    numpy.testing.assert_array_almost_equal(fieldDistances(record_pairs, 
                                                           deduper.data_model),
                                            numpy.array([[0, 0.647, 0, 0, 0]]), 3)

    record_pairs = (({'name' : 'steve', 'source' : 'b'}, 
                     {'name' : 'steven', 'source' : 'b'}),)
    numpy.testing.assert_array_almost_equal(fieldDistances(record_pairs, 
                                                           deduper.data_model),
                                            numpy.array([[1, 0.647, 0, 0.647, 0]]), 3)

    record_pairs = (({'name' : 'steve', 'source' : 'a'}, 
                     {'name' : 'steven', 'source' : 'b'}),)
    numpy.testing.assert_array_almost_equal(fieldDistances(record_pairs, 
                                                           deduper.data_model),
                                            numpy.array([[0, 0.647, 1, 0, 0.647]]), 3)

  def test_comparator(self) :
    fieldDistances = dedupe.core.fieldDistances
    deduper = dedupe.Dedupe({'type' : {'type' : 'Categorical',
                                       'Categories' : ['a', 'b', 'c']}
                             }, [])

    record_pairs = (({'type' : 'a'},
                     {'type' : 'b'}),
                    ({'type' : 'a'},
                     {'type' : 'c'}))

    numpy.testing.assert_array_almost_equal(fieldDistances(record_pairs, 
                                                           deduper.data_model),
                                            numpy.array([[ 0, 0, 1, 0, 0],
                                                         [ 0, 0, 0, 1, 0]]),
                                            3)

    deduper = dedupe.Dedupe({'type' : {'type' : 'Categorical',
                                       'Categories' : ['a', 'b', 'c']},
                             'source' : {'type' : 'Source',
                                         'Source Names' : ['foo', 'bar']}
                             }, [])

    record_pairs = (({'type' : 'a',
                      'source' : 'bar'},
                     {'type' : 'b',
                      'source' : 'bar'}),
                    ({'type' : 'a', 
                      'source' : 'foo'},
                     {'type' : 'c',
                      'source' : 'bar'}))


    numpy.testing.assert_array_almost_equal(fieldDistances(record_pairs, 
                                                           deduper.data_model),
         numpy.array([[ 1, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 0.],
                      [ 0, 0, 1, 0, 0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 0, 0.]]),
                                            3)

 

  def test_field_distance_interaction(self) :
    fieldDistances = dedupe.core.fieldDistances
    deduper = dedupe.Dedupe({'first_name' : {'type' :'String'},
                             'last_name' : {'type' : 'String'},
                             'first-last' : {'type' : 'Interaction', 
                                             'Interaction Fields' : ['first_name', 
                                                                     'last_name']},
                             'source' : {'type' : 'Source',
                                         'Source Names' : ['a', 'b']}
                           }, [])

    record_pairs = (({'first_name' : 'steve', 
                      'last_name' : 'smith', 
                      'source' : 'b'}, 
                     {'first_name' : 'steven', 
                      'last_name' : 'smith', 
                      'source' : 'b'}),)

    # ['source', 'first_name', 'last_name', 'different sources',
    # 'first-last', 'source:first_name', 'different sources:first_name',
    # 'source:last_name', 'different sources:last_name',
    # 'source:first-last', 'different sources:first-last']
    numpy.testing.assert_array_almost_equal(fieldDistances(record_pairs, 
                                                           deduper.data_model),
                                            numpy.array([[ 1.0,  
                                                           0.647,  
                                                           0.5,  
                                                           0.0,
                                                           0.323,
                                                           0.647,
                                                           0.0,
                                                           0.5,
                                                           0.0,
                                                           0.323,
                                                           0.0]]),
                                            3)
if __name__ == "__main__":
    unittest.main()