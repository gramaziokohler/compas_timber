from collections import OrderedDict
import random


class Nester(object):
    def __init__(self):
        pass

    def shuffle(self, lst):
        random.shuffle(lst)

    def space_remaining(self, bin):
        if len(bin) == 0:
            return self.stock_length
        return self.stock_length - (sum([beam.blank_length for beam in bin]))

    def sorted_dict(self, bin_dict):
        if len(bin_dict.items()) < 2:
            return bin_dict
        bin_list = sorted(bin_dict.values(), key=lambda x: self.space_remaining(x))
        dict = OrderedDict()
        for i in range(len(bin_list)):
            dict[i] = bin_list[i]
        return dict

    def total_space(self, bin_dict):
        return sum([self.space_remaining(bin) for bin in bin_dict.values()])

    def get_initial_bins(self, beams):
        bins = OrderedDict([(0, [])])
        for beam in beams:
            fits = False
            bins = self.sorted_dict(bins)
            for bin in bins.values():
                if self.space_remaining(bin) >= beam.blank_length:
                    bin.append(beam)
                    fits = True
                    break
            if not fits:
                bins[str(len(bins))] = [beam]
        return bins

    def fill_bins(self, bins, beams):
        for beam in beams:
            fits = False
            bins = self.sorted_dict(bins)
            for bin in bins.values():
                if self.space_remaining(bin) >= beam.blank_length:
                    bin.append(beam)
                    fits = True
                    break
            if not fits:
                bins[str(len(bins))] = [beam]
        return bins

    def parse_bins(self, bin_dict):
        dict_out = {"done": False}
        dict_out["finished_bins"] = bin_dict
        if self.total_space(bin_dict) < self.stock_length:
            dict_out["done"] = True
            return dict_out

        else:
            recycled_beams = []
            temporary_bins = OrderedDict()
            for bin in bin_dict.values():
                if self.space_remaining(bin) > self.tolerance:
                    recycled_beams.extend(bin)
                else:
                    temporary_bins[str(len(temporary_bins))] = bin
            dict_out["temporary_bins"] = temporary_bins
            dict_out["recycled_beams"] = recycled_beams
            return dict_out

    def get_bins(self, beams, stock_length, tolerance=1, iterations=10):
        self.stock_length = stock_length
        self.tolerance = tolerance
        if tolerance is None:
            self.tolerance = 1
        if iterations is None:
            iterations = 10

        self.total_length = sum([beam.blank_length for beam in beams])
        sort = False
        bins_out = None
        all_bins = []
        solved = False

        for i in range(iterations):
            if solved:
                break
            these_beams = beams
            these_bins = self.get_initial_bins(these_beams)
            results_dict = self.parse_bins(these_bins)
            if results_dict["done"]:
                bins_out = results_dict["finished_bins"]
            else:
                for x in range(iterations):
                    if sort:
                        beams_sorted = sorted(results_dict["recycled_beams"], key=lambda z: z.length, reverse=True)
                    else:
                        beams_sorted = results_dict["recycled_beams"]
                        self.shuffle(beams_sorted)

                    temp_bins = self.fill_bins(results_dict["temporary_bins"], beams_sorted)

                    results_dict = self.parse_bins(temp_bins)

                    if results_dict["done"]:
                        bins_out = results_dict["finished_bins"]
                        print("success after {0} iterations.".format(x))
                        solved = True
                        break
                    elif x == iterations - 1:
                        all_bins.append(results_dict["finished_bins"])
                    else:
                        sort = not sort

        if not bins_out:
            bins_out = min(all_bins, key=lambda x: len(x))

        beam_list_out = []
        for val in bins_out.values():
            beam_list_out.extend(val)

        if set(beam_list_out) != set(beams):
            raise Exception("beams inputs and outputs dont match")

        return bins_out
