"""Plateau timing and residual semantics, independent of encoded-film controls."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from taste_common import compare_curve, noise_sigma, peak_center, peak_intervals, zscore
from taste_lint import weakest
from threshold_registry import entry


class RoundSix(unittest.TestCase):
    def test_plateau_overshoot_sag_and_twenty_noise_seeds(self):
        t=np.arange(0,32,.1)
        for start in (18,24):
            design=[[0,.1],[start,.9],[30,.9],[32,.3]]
            y=np.interp(t,*np.array(design).T)
            for seed in range(20):
                for noise in (.006,.01,.02):
                    with self.subTest(start=start,seed=seed,noise=noise):
                        measured=y+np.random.default_rng(seed).normal(0,noise*np.ptp(y),len(t))
                        c=compare_curve(t,zscore(measured),design,proxy=True)
                        self.assertEqual(c['peak_offset_bars'],0)
                        self.assertFalse(c['revise'])
                        self.assertEqual(c['deviations'],[])
            for centre in (start+.2,29.8):
                measured=y+.03*np.exp(-((t-centre)/.3)**2)-.01*np.exp(-((t-27)/.5)**2)
                self.assertEqual(compare_curve(t,measured,design)['peak_offset_bars'],0)

    def test_nearest_edge_and_floating_point_boundary(self):
        t=np.arange(0,40,.1);design=[[0,.1],[18,.9],[30,.9],[40,.1]]
        y=np.interp(t,*np.array(design).T)
        for peak,offset,revise in ((17.,.5,False),(32.+4e-15,1.,False),(32.01,1.005,True)):
            with self.subTest(peak=peak),patch('taste_common.peak_center',return_value=peak):
                c=compare_curve(t,y,design)
                self.assertAlmostEqual(c['peak_offset_bars'],offset)
                self.assertEqual(c['revise'],revise)

    def test_disconnected_peaks_do_not_average_across_valley(self):
        t=np.arange(10.)
        self.assertAlmostEqual(peak_center(t,[0,0,1,1,0,0,1,1,0,0]),2.5)
        self.assertEqual(peak_intervals(np.array([[0,0],[2,1],[3,1],[4,0],[6,1],[7,1],[9,0]])),
                         [[2.,3.],[6.,7.]])
        self.assertIsNone(peak_center(t,np.ones(10)))

    def test_noise_estimate_tracks_measured_noise_not_range(self):
        rng=np.random.default_rng(9);jitter=rng.normal(0,.01,10000)
        self.assertAlmostEqual(noise_sigma(jitter),.01,delta=.0004)
        self.assertAlmostEqual(noise_sigma(jitter+np.arange(len(jitter))*.01),noise_sigma(jitter))
        self.assertAlmostEqual(noise_sigma(jitter*2),noise_sigma(jitter)*2)

    def test_excess_is_not_a_missing_deviation(self):
        t=np.arange(0,30,.1);design=[[0,.1],[15,.9],[30,.1]]
        y=np.interp(t,*np.array(design).T)+.2
        c=compare_curve(t,y,design)
        self.assertEqual(c['deviations'],[])
        self.assertIsNone(weakest(dict(M15=dict(times=t,values=y,components={}),comparison=c))['start'])
        flat=compare_curve(t,np.ones(len(t))*.8,[[0,.2],[30,.2]])
        self.assertTrue(all(d['kind']=='exceeds design' and d['deficit']<0 for d in flat['deviations']))

    def test_calibrated_residual_tolerance_shared_with_weakest(self):
        rule=entry('taste.curve.residual.max')
        self.assertEqual(rule['class'],'C');self.assertEqual(rule['provenance']['source_class'],'ANCHOR')
        t=np.arange(0,30,.1);design=[[0,.1],[18,.9],[30,.9]]
        original=np.interp(t,*np.array(design).T)
        for deficit,missing in ((.05,False),(.07,False),(.2,True)):
            y=original.copy();y[(t>=23)&(t<25)]-=deficit
            c=compare_curve(t,y,design,proxy=True)
            w=weakest(dict(M15=dict(times=t,values=y,components={}),comparison=c))
            self.assertEqual(bool(c['deviations']),missing)
            self.assertEqual(w['start'] is not None,missing)
            self.assertEqual(c['residual_tolerance'],rule['value'])


if __name__=='__main__':unittest.main()
