"""Blotter is a bingo callback for use from the client side 

GETs allow you to check the user's experiment status from within js while 
POSTs allow you to score conversions for a given test

"""
import os
import logging

from google.appengine.ext.webapp import RequestHandler

from .gae_bingo import bingo, ab_test
from .cache import bingo_and_identity_cache
from .stats import describe_result_in_words
from .config import can_control_experiments
import simplejson as json


class AB_Test(RequestHandler):
    """request user alternative/state for an experiment by passing 
    { canonical_name : "experiment_name" }
    
    successful requests return 200 and a json object { "experiment_name" : "state" }
    where state is a jsonified version of the user's state in the experiment
    
    if a user can_control_experiments, requests may create experiments on the server
    similar to calling ab_test directly. You should pass in:
    { "canonical_name": <string>, "alternative_params": <json_obj>, "conversion_name": <json_list>}
    This will return a 201 and the jsonified state of the user calling ab_test
    
    failed requests return 404 if the experiment is not found and
    return a 400 if the params are passed incorrectly
    """
    
    def post(self):
        
        experiment_name = self.request.get("canonical_name", None)
        alternative_params = self.request.get("alternative_params", None)
        
        if alternative_params:
            alternative_params = json.loads(alternative_params)
        
        bingo_cache, bingo_identity_cache = bingo_and_identity_cache()
        conversion_name = self.request.get("conversion_name", None)
        
        if conversion_name:
            conversion_name = json.loads(conversion_name)
        
        self.response.headers['Content-Type'] = 'text/json'
        
        if experiment_name:
            
            if experiment_name not in bingo_cache.experiments:
                
                if can_control_experiments():
                    # create the given ab_test with passed params, etc
                    alternative = ab_test(experiment_name, alternative_params, conversion_name)
                    logging.info("blotter created ab_test: %s", experiment_name)
                    self.response.set_status(201)
                    self.response.out.write(json.dumps(alternative))
                    return
                
                else:
                    # experiment not found (and not being created)
                    self.response.set_status(404)
                    return
            
            # return status for experiment (200 implicit)
            else:
                alternative = ab_test(experiment_name)
                self.response.out.write(json.dumps(alternative))
                return
        
        else:
            # no params passed, sorry broheim
            self.response.set_status(400)
            self.response.out.write('"hc svnt dracones"')
            return
    


class Bingo(RequestHandler):
    """post a conversion to gae_bingo by passing { convert : "conversion_name" }
    
    you cannot currently pass a json list (as the response would be a bit ambiguous)
    so instead pass multiple calls to post (which is what the js tool does)
    
    successful conversions return HTTP 204
    
    failed conversions return a 404 (i.e. experiment not found in reverse-lookup)
    
    no params returns a 400 error
    """

    def post(self):
        
        bingo_cache, bingo_identity_cache = bingo_and_identity_cache()
        
        conversion = self.request.get("convert", None)
        if conversion:
            conversion = json.loads(conversion)

        self.response.headers['Content-Type'] = 'text/json'

        experiment_names = bingo_cache.get_experiment_names_by_conversion_name(conversion)
        if conversion:
            
            if len(experiment_names) > 0:
                # send null message
                self.response.set_status(204)
                # score the conversion
                bingo(conversion)
                return
            
            else:
                # send error
                self.response.set_status(404)
                return
        
        else:
            # no luck, compadre
            self.response.set_status(400)
            self.response.out.write('"hc svnt dracones"')
    
