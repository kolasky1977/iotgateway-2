
'''
__author__ = "sgript"

Expected request format:
{
'enquiry': '',               # Boolean, if used all rest parameters are unneeded, module_name can be optionally checked.
'module_name': '',           # Use this to find applicable methods?
'id': '',                    # If applicable, i.e. Philips Hue
'device_type': '',           # Will define fixed categories later.
'requested_function': '',    # NOTE: See ast module ***
'parameters': ''
}

# NOTE: When just listing devices all parameters can be

TODO: This is to be handled by a single-service function (likely messages) branching to applicable functions.

'''

import sys
import json
import inspect
from importlib import util
from helpers import module_methods, list_modules as lm
from modules import philapi

from pubnub.enums import PNStatusCategory
from pubnub.callbacks import SubscribeCallback
from pubnub.pubnub import PubNub, SubscribeListener
from pubnub.pnconfiguration import PNConfiguration, PNReconnectionPolicy


def my_publish_callback(envelope, status):
    if not status.is_error():
        print("GatewayReceiver: Message successfully sent to client.")
        pass
    else:
        print("GatewayReceiver: Error transmitting message to client.")
        pass

class Receiver(SubscribeCallback):
    def __init__(self):
        # TODO: Need to define a way to find this auth key.
        # Passed straight from the gateway_auth?
        # Text file?
        # Etc. IMPORTANT
        self.pnconfig = PNConfiguration()
        self.channel = '' # REVIEW: PROBABLY DO NOT NEED THIS HERE
        self.pnconfig.uuid = self.uuid = 'gateway'
        self.pnconfig.subscribe_key = self.subscribe_key = 'sub-c-12c2dd92-860f-11e7-8979-5e3a640e5579'
        self.pnconfig.publish_key = self.publish_key = 'pub-c-85d5e576-5d92-48b0-af83-b47a7f21739f'
        self.pnconfig.reconnect_policy = PNReconnectionPolicy.LINEAR
        self.pnconfig.ssl = True
        self.pnconfig.subscribe_timeout = self.pnconfig.connect_timeout = self.pnconfig.non_subscribe_timeout = 9^99
        self.pubnub = PubNub(self.pnconfig)

    def subscribe_channel(self, channel_name, auth_key):
        self.pnconfig.auth_key = auth_key
        self.channel = channel_name
        self.pubnub = PubNub(self.pnconfig)
        self.pubnub.add_listener(self)

        self.pubnub.subscribe().channels(channel_name).execute()

    def publish_request(self, channel, msg):
        # REVIEW: May need to format py to json
        msg_json = json.loads(json.dumps(msg))
        self.pubnub.publish().channel(channel).message(msg_json).async(my_publish_callback)

    def presence(self, pubnub, presence):
        #print(presence.channel)
        pass  # handle incoming presence data

    def status(self, pubnub, status):
        if status.category == PNStatusCategory.PNUnexpectedDisconnectCategory:
            pass  # This event happens when radio / connectivity is lost

        elif status.category == PNStatusCategory.PNConnectedCategory:
            print('connected?')
            pass

        elif status.category == PNStatusCategory.PNReconnectedCategory:
            pass

        elif status.category == PNStatusCategory.PNDecryptionErrorCategory:
            pass

    def message(self, pubnub, message):
        msg = message.message
        print(msg)

        if 'enquiry' in msg and msg['enquiry'] is True:
            # TODO: Still need something to list available modules.
            if 'module_name' in msg:
                module_found = True if util.find_spec("modules."+msg['module_name']) != None else False

                # Maybe since there was something supplied, instead of False just call a publish to tell them
                # They mispelled or something.

                if module_found:

                    methods = module_methods.find(msg['module_name']) # Gets module's methods (cannot be inside a class)

                    module = sys.modules['modules.' + msg['module_name']]

                    dictionary_of_functions = {}
                    for method in methods:
                        function = getattr(module, method)
                        dictionary_of_functions[method] = inspect.getargspec(function)[0]

                    enquiry_response = {"module_name": msg['module_name']}
                    enquiry_response['enquiry'] = dictionary_of_functions

                    available_functions_resp = json.loads(json.dumps(enquiry_response))

                    pubnub.publish().channel(message.channel).message(available_functions_resp).async(my_publish_callback)

            # Else if no module name supplied just show list of them available.
            elif 'module_name' not in msg and msg['enquiry'] is False:
                dictionary_of_modules = json.loads(json.dumps({"enquiry": {"modules": lm.list_modules()}}))

                pubnub.publish().channel(message.channel).message(dictionary_of_modules).async(my_publish_callback)

        elif 'enquiry' not in msg or msg['enquiry'] is False:
            if 'requested_function' in msg:
                if 'module_name' in msg:
                    module_found = True if util.find_spec("modules."+msg['module_name']) != None else False

                    if module_found:
                        module = sys.modules['modules.' + msg['module_name']]

                        try:
                            method_requested = getattr(module, msg['requested_function'])
                            method_args = inspect.getargspec(method_requested)[0]

                            if not msg['parameters'] and method_args is not None: # needs params but not provided
                                print('You did not provide parameters that the method requires!')

                                result = {'result': method_requested()}
                                self.publish_request(message.channel, result)

                            elif msg['parameters'] and method_args is not None: # params provided and needed
                                result = json.loads(json.method_requested(*msg['parameters'])[1:-1])
                                pubnub.publish().channel(message.channel).message(result).async(my_publish_callback)

                        except AttributeError as e:
                            print("GatewayReceiverError: The method you requested does not exist.\n" + e.message)

                else:
                    print("error no module name supplied even when not an enquiry") # tidy up later


        # TODO: IMPORTANT: Before carrying out calls, need to negotiate some security policy...

        pass


if __name__ == "__main__":
    receiver = Receiver()
    receiver.subscribe_channel('NO40ACE6I6', 'V3SIPF92JQ')