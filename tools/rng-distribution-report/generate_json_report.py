import base64
import csv
import hashlib
import json
import os
import time
import zlib
from enum import Enum
from datetime import datetime


class RngDataEntryFields(Enum):
    TYPE = "type"
    VARIANT = "variant"
    CONTEXT = "context"
    RANGE = "range"
    CHANCE = "chance"
    WEIGHTS = "weights"
    ELEMENTS = "elements"
    RESULT = "result"
    ELEMENT = "element"

class RngDataEntryTypes(Enum):
    RANDOM_WEIGHTS = "randomWeighted"
    RANDOM_INDEX = "randomIndex"
    HAS_CHANCE = "hasChance"



class RngStatsProcessor:
    def __init__(self):
        self._processedSpins = 0
        self._start_time = time.time()
        self._RANGE_LIMIT = 1_000_000
        self._rng_report = {
            "stats": {
                "processedRngCalls": 0,
                "uniqueContexts": 0,            # contexts with the same name but different variant counts as unique
                "uniqueWeightSets": 0,
                "statsPerVariant": {}
            },
            "rng_distribution": {
                "variants": {}
            }
        }

    def process_data_extract_file(self, file_name):
        self._start_time = time.time()
        print(f"start processing file: {file_name}")


        # open and process file
        with open(file_name, newline='', encoding='utf-8') as csvfile:
            # create reader
            reader = csv.reader(csvfile)

            # skip header
            headers = next(reader)
            header_map = {name: idx for idx, name in enumerate(headers)}

            # process data extract file line by line (spin by spin)
            for row in reader:
                self._process_single_data_extract_spin(row, header_map)
                self._print_progress()

    def save_report_json(self, file_name):
        sorted_dict = dict(sorted(self._rng_report.items()))

        with open(file_name, 'w') as file:
            json.dump(sorted_dict, file, indent=4)

    def _process_single_data_extract_spin(self, data_extract_row, header_map):
        self._processedSpins = self._processedSpins + 1

        # extract data from current row
        command = data_extract_row[header_map["Command"]]
        extra_parameters = data_extract_row[header_map["AdditionalParameters"]]

        # skip if collect command (command used only to pay win to the player, no RNG used)
        if command == "CollectCommand":
            return

        # skip if no extra parameters (Commands similar to CollectCommand, like ContinueCommand in Pirates3)
        if extra_parameters == "":
            return

        # get rng data list (this list describe all rng calls in single spin)
        rng_data = self._extract_rng_data_from_extra_parameters(extra_parameters)

        # skip if no RNG data
        if rng_data is None:
            return

        # process all RNG calls
        for rng_data_entry in rng_data:
            self._process_single_rng_data_entry(rng_data_entry)


    def _process_single_rng_data_entry(self, rng_data_entry):
        self._rng_report["stats"]["processedRngCalls"] = self._rng_report["stats"]["processedRngCalls"] + 1

        # get data
        random_type = rng_data_entry[RngDataEntryFields.TYPE.value]
        variant = rng_data_entry[RngDataEntryFields.VARIANT.value]
        context = rng_data_entry[RngDataEntryFields.CONTEXT.value]

        # skip if the range is too large (especially randomIndex with MAX_INT), as we do not run more than a couple of million simulations
        # for the RNG report, so the data would not provide meaningful statistical information anyway.
        if rng_data_entry["range"] > self._RANGE_LIMIT and random_type != RngDataEntryTypes.HAS_CHANCE.value:
            return

        # if given variant not yet in rng report, create new object for this variant
        if variant not in self._rng_report["rng_distribution"]["variants"]:
            self._rng_report["rng_distribution"]["variants"][variant] = {}

            # create stats for new variant
            self._rng_report["stats"]["statsPerVariant"][variant] = {
                "uniqueContexts": 0,  # contexts with the same name but different variant counts as unique
                "uniqueWeightSets": 0,
                "weightSetsPerContext": {}
            }

        # if given variant:context not yet in rng report, create new object for this context
        if context not in self._rng_report["rng_distribution"]["variants"][variant]:
            # create context
            self._rng_report["rng_distribution"]["variants"][variant][context] = {}

            # update stats
            self._rng_report["stats"]["uniqueContexts"] = self._rng_report["stats"]["uniqueContexts"] + 1
            self._rng_report["stats"]["statsPerVariant"][variant]["uniqueContexts"] = self._rng_report["stats"]["statsPerVariant"][variant]["uniqueContexts"] + 1

        # process RNG entry based on type
        if random_type == RngDataEntryTypes.RANDOM_INDEX.value:
            self._process_random_index_entry(rng_data_entry)

        if random_type == RngDataEntryTypes.RANDOM_WEIGHTS.value:
            self._process_random_weighted_entry(rng_data_entry)

        if random_type == RngDataEntryTypes.HAS_CHANCE.value:
            self._process_has_chance_entry(rng_data_entry)


    def _process_random_index_entry(self, rng_data_entry):
        # get specific elements
        random_type = rng_data_entry[RngDataEntryFields.TYPE.value]
        variant = rng_data_entry[RngDataEntryFields.VARIANT.value]
        context = rng_data_entry[RngDataEntryFields.CONTEXT.value]
        rng_range = rng_data_entry[RngDataEntryFields.RANGE.value]
        result = rng_data_entry[RngDataEntryFields.RESULT.value]

        # calculate hash, so every different set of weights/elements is tracked separately
        hash_text = random_type + variant + context + str(rng_range)
        hash_md5 = hashlib.md5(hash_text.encode('utf-8')).hexdigest()

        # get current context
        current_context = self._rng_report["rng_distribution"]["variants"][variant][context]

        # add entry for current hash if not present yet
        if hash_md5 not in current_context:
            current_context[hash_md5] = {
                "type": random_type,
                "variant": variant,
                "context": context,
                "range": rng_range,
                "hitTable": {i: 0 for i in range(rng_range)},
                "runStatsRng": {"up": 0, "down": 0, "same": 0},
                "runStatsElements": {"up": 0, "down": 0, "same": 0},
                "meta": {
                    "hashText": hash_text,
                    "hash": hash_md5,
                    "first": True,
                    "lastElement": "",
                    "lastRngNumber": 0,
                    "numberOfCalls": 0
                }
            }

            # update stats
            self._rng_report["stats"]["uniqueWeightSets"] = self._rng_report["stats"]["uniqueWeightSets"] + 1
            self._rng_report["stats"]["statsPerVariant"][variant]["uniqueWeightSets"] = self._rng_report["stats"]["statsPerVariant"][variant]["uniqueWeightSets"] + 1

            if context not in self._rng_report["stats"]["statsPerVariant"][variant]["weightSetsPerContext"]:
                self._rng_report["stats"]["statsPerVariant"][variant]["weightSetsPerContext"][context] = 0

            self._rng_report["stats"]["statsPerVariant"][variant]["weightSetsPerContext"][context] = self._rng_report["stats"]["statsPerVariant"][variant]["weightSetsPerContext"][context] + 1



        # get current stats table
        current_hash_table = current_context[hash_md5]

        # update meta
        current_hash_table["meta"]["numberOfCalls"] = current_hash_table["meta"]["numberOfCalls"] + 1

        # update hit table
        hit_table = current_hash_table["hitTable"]
        if result not in hit_table:
            hit_table[int(result)] = 0

        hit_table[result] = hit_table[result] + 1

        # update run statistics
        if current_hash_table["meta"]["first"]:
            current_hash_table["meta"]["first"] = False
            current_hash_table["meta"]["lastElement"] = result
            current_hash_table["meta"]["lastRngNumber"] = result
        else:
            # update rng run statistics
            if current_hash_table["meta"]["lastRngNumber"] == result:
                current_hash_table["runStatsRng"]["same"] = current_hash_table["runStatsRng"]["same"] + 1
            if current_hash_table["meta"]["lastRngNumber"] < result:
                current_hash_table["runStatsRng"]["up"] = current_hash_table["runStatsRng"]["up"] + 1
            if current_hash_table["meta"]["lastRngNumber"] > result:
                current_hash_table["runStatsRng"]["down"] = current_hash_table["runStatsRng"]["down"] + 1

            current_hash_table["meta"]["lastRngNumber"] = result

            # update elements run statistics
            if current_hash_table["meta"]["lastElement"] == result:
                current_hash_table["runStatsElements"]["same"] = current_hash_table["runStatsElements"]["same"] + 1
            if current_hash_table["meta"]["lastElement"] < result:
                current_hash_table["runStatsElements"]["up"] = current_hash_table["runStatsElements"]["up"] + 1
            if current_hash_table["meta"]["lastElement"] > result:
                current_hash_table["runStatsElements"]["down"] = current_hash_table["runStatsElements"]["down"] + 1

            current_hash_table["meta"]["lastElement"] = result

    def _process_random_weighted_entry(self, rng_data_entry):
        # get specific elements
        random_type = rng_data_entry[RngDataEntryFields.TYPE.value]
        variant = rng_data_entry[RngDataEntryFields.VARIANT.value]
        context = rng_data_entry[RngDataEntryFields.CONTEXT.value]
        rng_range = rng_data_entry[RngDataEntryFields.RANGE.value]
        element = rng_data_entry[RngDataEntryFields.ELEMENT.value]
        elements = rng_data_entry[RngDataEntryFields.ELEMENTS.value]
        weights = rng_data_entry[RngDataEntryFields.WEIGHTS.value]
        result = rng_data_entry[RngDataEntryFields.RESULT.value]

        # calculate hash, so every different set of weights/elements is tracked separately
        hash_text = random_type + variant + context + str(rng_range) + str(elements) + str(weights)
        hash_md5 = hashlib.md5(hash_text.encode('utf-8')).hexdigest()

        # get current context
        current_context = self._rng_report["rng_distribution"]["variants"][variant][context]


        # add entry for current hash if not present yet
        if hash_md5 not in current_context:
            current_context[hash_md5] = {
                "type": random_type,
                "variant": variant,
                "context": context,
                "range": rng_range,
                "elements": elements,
                "weights": weights,
                "hitTable": {key: 0 for key in elements},
                "runStatsRng": {"up": 0, "down": 0, "same": 0},
                "runStatsElements": {"up": 0, "down": 0, "same": 0},
                "meta": {
                    "hashText": hash_text,
                    "hash": hash_md5,
                    "first": True,
                    "lastElement": "",
                    "lastRngNumber": 0,
                    "numberOfCalls": 0
                }
            }

            # update stats
            self._rng_report["stats"]["uniqueWeightSets"] = self._rng_report["stats"]["uniqueWeightSets"] + 1
            self._rng_report["stats"]["statsPerVariant"][variant]["uniqueWeightSets"] = self._rng_report["stats"]["statsPerVariant"][variant]["uniqueWeightSets"] + 1

            if context not in self._rng_report["stats"]["statsPerVariant"][variant]["weightSetsPerContext"]:
                self._rng_report["stats"]["statsPerVariant"][variant]["weightSetsPerContext"][context] = 0

            self._rng_report["stats"]["statsPerVariant"][variant]["weightSetsPerContext"][context] = self._rng_report["stats"]["statsPerVariant"][variant]["weightSetsPerContext"][context] + 1


        # get current stats table
        current_hash_table = current_context[hash_md5]

        # update meta
        current_hash_table["meta"]["numberOfCalls"] = current_hash_table["meta"]["numberOfCalls"] + 1

        # update hit table
        hit_table = current_hash_table["hitTable"]
        if element not in hit_table:
            hit_table[element] = 0

        hit_table[element] = hit_table[element] + 1

        # update run statistics
        if current_hash_table["meta"]["first"]:
            current_hash_table["meta"]["first"] = False
            current_hash_table["meta"]["lastElement"] = element
            current_hash_table["meta"]["lastRngNumber"] = result
        else:
            # update rng run statistics
            if current_hash_table["meta"]["lastRngNumber"] == result:
                current_hash_table["runStatsRng"]["same"] = current_hash_table["runStatsRng"]["same"] + 1
            if current_hash_table["meta"]["lastRngNumber"] < result:
                current_hash_table["runStatsRng"]["up"] = current_hash_table["runStatsRng"]["up"] + 1
            if current_hash_table["meta"]["lastRngNumber"] > result:
                current_hash_table["runStatsRng"]["down"] = current_hash_table["runStatsRng"]["down"] + 1

            current_hash_table["meta"]["lastRngNumber"] = result

            # update elements run statistics
            if elements.index(current_hash_table["meta"]["lastElement"]) == elements.index(element):
                current_hash_table["runStatsElements"]["same"] = current_hash_table["runStatsElements"]["same"] + 1
            if elements.index(current_hash_table["meta"]["lastElement"]) < elements.index(element):
                current_hash_table["runStatsElements"]["up"] = current_hash_table["runStatsElements"]["up"] + 1
            if elements.index(current_hash_table["meta"]["lastElement"]) > elements.index(element):
                current_hash_table["runStatsElements"]["down"] = current_hash_table["runStatsElements"]["down"] + 1

            current_hash_table["meta"]["lastElement"] = element


    def _process_has_chance_entry(self, rng_data_entry):
        # get specific elements
        random_type = rng_data_entry[RngDataEntryFields.TYPE.value]
        variant = rng_data_entry[RngDataEntryFields.VARIANT.value]
        context = rng_data_entry[RngDataEntryFields.CONTEXT.value]
        rng_range = rng_data_entry[RngDataEntryFields.RANGE.value]
        chance = rng_data_entry[RngDataEntryFields.CHANCE.value]
        element = rng_data_entry[RngDataEntryFields.ELEMENT.value]
        result = rng_data_entry[RngDataEntryFields.RESULT.value]

        # calculate hash, so every different set of weights/elements is tracked separately
        hash_text = random_type + variant + context + str(rng_range) + str(chance)
        hash_md5 = hashlib.md5(hash_text.encode('utf-8')).hexdigest()

        # get current context
        current_context = self._rng_report["rng_distribution"]["variants"][variant][context]

        # add entry for current hash if not present yet
        if hash_md5 not in current_context:
            current_context[hash_md5] = {
                "type": random_type,
                "variant": variant,
                "context": context,
                "range": rng_range,
                "chance": chance,
                "hitTable": {"True": 0, "False": 0},
                "runStatsRng": {"up": 0, "down": 0, "same": 0},
                "runStatsElements": {"up": 0, "down": 0, "same": 0},
                "meta": {
                    "hashText": hash_text,
                    "hash": hash_md5,
                    "first": True,
                    "lastElement": "",
                    "lastRngNumber": 0,
                    "numberOfCalls": 0
                }
            }

            # update stats
            self._rng_report["stats"]["uniqueWeightSets"] = self._rng_report["stats"]["uniqueWeightSets"] + 1
            self._rng_report["stats"]["statsPerVariant"][variant]["uniqueWeightSets"] = self._rng_report["stats"]["statsPerVariant"][variant]["uniqueWeightSets"] + 1

            if context not in self._rng_report["stats"]["statsPerVariant"][variant]["weightSetsPerContext"]:
                self._rng_report["stats"]["statsPerVariant"][variant]["weightSetsPerContext"][context] = 0

            self._rng_report["stats"]["statsPerVariant"][variant]["weightSetsPerContext"][context] = self._rng_report["stats"]["statsPerVariant"][variant]["weightSetsPerContext"][context] + 1


        # get current stats table
        current_hash_table = current_context[hash_md5]

        # update meta
        current_hash_table["meta"]["numberOfCalls"] = current_hash_table["meta"]["numberOfCalls"] + 1

        # update hit table
        hit_table = current_hash_table["hitTable"]
        if element not in hit_table:
            hit_table[element] = 0

        hit_table[element] = hit_table[element] + 1

        # update run statistics
        if current_hash_table["meta"]["first"]:
            current_hash_table["meta"]["first"] = False
            current_hash_table["meta"]["lastElement"] = element
            current_hash_table["meta"]["lastRngNumber"] = result
        else:
            # update rng run statistics
            if current_hash_table["meta"]["lastRngNumber"] == result:
                current_hash_table["runStatsRng"]["same"] = current_hash_table["runStatsRng"]["same"] + 1
            if current_hash_table["meta"]["lastRngNumber"] < result:
                current_hash_table["runStatsRng"]["up"] = current_hash_table["runStatsRng"]["up"] + 1
            if current_hash_table["meta"]["lastRngNumber"] > result:
                current_hash_table["runStatsRng"]["down"] = current_hash_table["runStatsRng"]["down"] + 1

            current_hash_table["meta"]["lastRngNumber"] = result

            # update elements run statistics
            elements = ["True", "False"]
            if current_hash_table["meta"]["lastElement"] == element:
                current_hash_table["runStatsElements"]["same"] = current_hash_table["runStatsElements"]["same"] + 1
            if elements.index(current_hash_table["meta"]["lastElement"]) < elements.index(element):
                current_hash_table["runStatsElements"]["up"] = current_hash_table["runStatsElements"]["up"] + 1
            if elements.index(current_hash_table["meta"]["lastElement"]) > elements.index(element):
                current_hash_table["runStatsElements"]["down"] = current_hash_table["runStatsElements"]["down"] + 1

            current_hash_table["meta"]["lastElement"] = element



    def _print_progress(self):
        elapsed = time.time() - self._start_time
        print(f"\rElapsed Time: {elapsed:.2f}s Processed Spins: {self._processedSpins} ", end="")


    # extracts rng data from data extract's extra parameters
    # returns parsed pythin dictionary (object)
    @staticmethod
    def _extract_rng_data_from_extra_parameters(extra_parameters):
        try:
            # separate extra parameters
            extra_parameters_list = extra_parameters.split("\n")

            # get rng extra parameters
            rng_data_wrapped = extra_parameters_list[1]

            # strip wrapper
            rng_data_base64 = rng_data_wrapped[9:-2]

            # decode base64
            rng_data_compressed_binary = base64.b64decode(rng_data_base64)

            # decompress deflate
            rng_data_binary = zlib.decompress(rng_data_compressed_binary, -zlib.MAX_WBITS)

            # encode as text (json)
            rng_data_json = rng_data_binary.decode('utf-8')

            # parse json to dict (object) and return
            return json.loads(rng_data_json)
        except:
            print("error during RNG data parsing.")
            return None


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Generate RNG distribution JSON report from a data extract CSV.")
    parser.add_argument("input", help="Path to the input CSV data extract file")
    parser.add_argument("output", help="Path for the output JSON report file")
    args = parser.parse_args()

    stats_processor = RngStatsProcessor()
    stats_processor.process_data_extract_file(args.input)
    stats_processor.save_report_json(args.output)

