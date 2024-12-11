from collections import OrderedDict
import random


class Nester(object):
    """Class for nesting beams into a stock beam


    Attributes
    ----------
    stock_length : float
        length of the stock beam in which to be nested
    tolerance : float
        tolerance for the nesting algorithm, if the remaining space in a bin is less than the tolerance, the bin is considered full
    total_length : float
        total length of all beams to be nested

    """

    def __init__(self):
        pass

    def shuffle(self, lst):
        random.shuffle(lst)

    def space_remaining(self, bin):
        """returns the space remaining in a bin"""
        if len(bin) == 0:
            return self.stock_length
        return self.stock_length - (sum([beam.blank_length for beam in bin]))

    def sorted_dict(self, bin_dict):
        """sorts a dictionary of bins by space remaining in each bin"""
        if len(bin_dict.items()) < 2:
            return bin_dict
        bin_list = sorted(bin_dict.values(), key=lambda x: self.space_remaining(x))
        dict = OrderedDict()
        for i in range(len(bin_list)):
            dict[i] = bin_list[i]
        return dict

    def total_space(self, bin_dict):
        """returns the total space remaining in all bins, AKA total waste"""
        return sum([self.space_remaining(bin) for bin in bin_dict.values()])

    def get_bins_basic(self, beams):
        """returns a dictionary of bins with beams nested in them"""
        beams_sorted = sorted(beams, key=lambda z: z.length, reverse=True)
        bins = OrderedDict([(0, [])])
        for beam in beams_sorted:
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

    def fill_bins(self, bins, beams, sort=True, shuffle=False):
        """fills a partial bins dictionary with beams, returns a dictionary of bins with beams nested in them"""
        if sort:
            beams_sorted = sorted(beams, key=lambda z: z.length, reverse=True)
        elif shuffle:
            beams_sorted = beams
            self.shuffle(beams_sorted)
        for beam in beams_sorted:
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

    def longest_cutoff(self, bin_dict):
        """returns the longest cutoff in a bin dictionary"""
        sorted_bins = self.sorted_dict(bin_dict)
        return [self.space_remaining(bin) for bin in sorted_bins.values()]

    def parse_bins(self, bin_dict):
        """evaluates the success of the nesting, returns a dictionary with the results of the nesting process"""
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

    def validate_bin_results(self, bins, beams):
        beam_list_out = []
        for val in bins.values():
            beam_list_out.extend(val)

        if set(beam_list_out) != set(beams):
            raise Exception("Beams input and nesting output dont match")

    def get_bins(self, beams, stock_length, tolerance=None, iterations=0):
        """returns a dictionary of bins with beams nested in them

        Parameters
        ----------
        beams : list(:class:`compas_timber.parts.Beam`)
            list of beams to be nested
        stock_length : float
            length of the stock beam in which to be nested
        tolerance : float
            tolerance for the nesting algorithm, if the remaining space in a bin is less than the tolerance, the bin is considered full
        iterations : int
            number of iterations to run the nesting algorithm, the algorithm will stop when the total waste is less than the stock length

        """
        self.stock_length = stock_length
        if tolerance is None:
            self.tolerance = stock_length / 100
        else:
            self.tolerance = tolerance
        if iterations is None:
            iterations = 0

        self.total_length = sum([beam.blank_length for beam in beams])
        bins_out = None
        all_bins = []

        if iterations == 0:
            return self.get_bins_basic(beams)

        else:
            for i in range(iterations):  # try with different shuffling
                these_beams = beams
                these_bins = self.get_bins_basic(these_beams)
                results_dict = self.parse_bins(these_bins)
                if results_dict["done"]:  # if the nesting is successful
                    bins_out = results_dict["finished_bins"]
                else:
                    sort = False
                    shuffle = True
                    for x in range(
                        iterations
                    ):  # tries to repack the beams that don't fit in the bins within the cutoff tolerance
                        these_beams = results_dict["recycled_beams"]
                        temp_bins = self.fill_bins(results_dict["temporary_bins"], these_beams, sort, shuffle)
                        results_dict = self.parse_bins(temp_bins)
                        if results_dict["done"]:
                            bins_out = results_dict["finished_bins"]
                            print("success after {0} iterations.".format(x))
                            break
                        elif x == iterations - 1:  # if the last iteration is reached, the best result is taken
                            all_bins.append(results_dict["finished_bins"])
                        else:
                            sort = not sort
                            shuffle = not shuffle
                if results_dict["done"]:
                    break

        if not bins_out:
            bins_out = min(
                all_bins, key=lambda x: len(x)
            )  # if no successful nesting is found, the one with the least bins is taken

        self.validate_bin_results(bins_out, beams)

        return bins_out
