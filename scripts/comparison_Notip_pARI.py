import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sys
from joblib import Memory
import os
from nilearn.datasets import fetch_neurovault

script_path = os.path.dirname(__file__)
fig_path_ = os.path.abspath(os.path.join(script_path, os.pardir))
fig_path = os.path.join(fig_path_, 'figures')

# Fetch data
fetch_neurovault(max_images=np.infty, mode='download_new', collection_id=1952)

sys.path.append(script_path)
from posthoc_fmri import compute_bounds, get_data_driven_template_two_tasks, calibrate_simes
from posthoc_fmri import get_processed_input, ari_inference, get_pivotal_stats_shifted
from sanssouci.reference_families import shifted_template, shifted_template_lambda
from sanssouci.lambda_calibration import calibrate_jer, get_pivotal_stats_shifted, calibrate_jer_param
from sanssouci import get_permuted_p_values_one_sample
from tqdm import tqdm
from scipy import stats
import sanssouci as sa

seed = 42
alpha = 0.05
B = 1000
n_train = 10000
k_max = 1000
k_min = 27
smoothing_fwhm = 4
n_jobs = 1

location = './cachedir'
memory = Memory(location, mmap_mode='r', verbose=0)

train_task1 = 'task001_vertical_checkerboard_vs_baseline'
train_task2 = 'task001_horizontal_checkerboard_vs_baseline'

get_data_driven_template_two_tasks = memory.cache(
                                    get_data_driven_template_two_tasks)

learned_templates = get_data_driven_template_two_tasks(
                    train_task1, train_task2, B=n_train, seed=seed)
learned_templates_kmin = learned_templates.copy()
learned_templates_kmin[:, :k_min] = np.zeros((n_train, k_min))

if len(sys.argv) > 1:
    n_jobs = int(sys.argv[1])
else:
    n_jobs = 1

df_tasks = pd.read_csv(os.path.join(script_path, 'contrast_list2.csv'))
test_task1s, test_task2s = df_tasks['task1'], df_tasks['task2']

pvals_perm_tot = np.load(os.path.join(script_path, "pvals_perm_tot.npy"),
                         mmap_mode="r")


def compute_bounds_comparison(task1s, task2s, learned_templates,
                              alpha, TDP, k_max, B,
                              smoothing_fwhm=4, n_jobs=1, seed=None, k_min=0):
    """
    Find largest FDP controlling regions on a list of contrast pairs
    using ARI, calibrated Simes and  learned templates.

    Parameters
    ----------

    task1s : list
        list of contrasts
    task2s : list
        list of contrasts
    learned_templates : array of shape (B_train, p)
        sorted quantile curves computed on training data
    alpha : float
        risk level
    k_max : int
        threshold families length
    B : int
        number of permutations at inference step
    smoothing_fwhm : float
        smoothing parameter for fMRI data (in mm)
    n_jobs : int
        number of CPUs used for computation. Default = 1

    Returns
    -------

    bounds_tot : matrix
        Size of largest FDP controlling regions for all three methods

    """
    notip_bounds = []
    pari_bounds = []

    for i in tqdm(range(len(task1s))):
        fmri_input, nifti_masker = get_processed_input(
                                                task1s[i], task2s[i],
                                                smoothing_fwhm=smoothing_fwhm)

        stats_, p_values = stats.ttest_1samp(fmri_input, 0)
        p = fmri_input.shape[1]
        # pval0 = sa.get_permuted_p_values_one_sample(fmri_input,
        #                                             B=B,
        #                                             seed=seed,
        #                                             n_jobs=n_jobs)

        pval0 = pvals_perm_tot[i]
        calibrated_shifted_template = calibrate_jer_param(alpha, shifted_template_lambda,
                                                          pval0, k_max=p, k_min=k_min)
        calibrated_tpl = calibrate_jer(alpha, learned_templates,
                                       pval0, k_max, k_min=k_min)

        _, region_size_notip = sa.find_largest_region(p_values, calibrated_tpl,
                                                      TDP,
                                                      nifti_masker)

        _, region_size_pari = sa.find_largest_region(p_values,
                                                     calibrated_shifted_template,
                                                     TDP,
                                                     nifti_masker)

        notip_bounds.append(region_size_notip)
        pari_bounds.append(region_size_pari)

    bounds_tot = np.vstack([notip_bounds, pari_bounds])
    return bounds_tot


# Compute largest region sizes for 3 possible TDP values

res_01 = compute_bounds_comparison(test_task1s, test_task2s, learned_templates_kmin, alpha,
                                   0.95, k_max, B, smoothing_fwhm=smoothing_fwhm,
                                   n_jobs=n_jobs,
                                   seed=seed, k_min=k_min)
np.save('/home/onyxia/work/Notip/figures/res_01.npy', res_01)

res_02 = compute_bounds_comparison(test_task1s, test_task2s, learned_templates_kmin, alpha,
                                   0.9, k_max, B, smoothing_fwhm=smoothing_fwhm,
                                   n_jobs=n_jobs,
                                   seed=seed, k_min=k_min)
np.save('/home/onyxia/work/Notip/figures/res_02.npy', res_02)

res_03 = compute_bounds_comparison(test_task1s, test_task2s, learned_templates_kmin, alpha,
                                   0.8, k_max, B, smoothing_fwhm=smoothing_fwhm,
                                   n_jobs=n_jobs,
                                   seed=seed, k_min=k_min)
np.save('/home/onyxia/work/Notip/figures/res_03.npy', res_03)

# res_01 = np.load("/home/onyxia/work/Notip/figures/res_01.npy")
# res_02 = np.load("/home/onyxia/work/Notip/figures/res_02.npy")
# res_03 = np.load("/home/onyxia/work/Notip/figures/res_03.npy")

# multiple boxplot code adapted from
# https://stackoverflow.com/questions/16592222/matplotlib-group-boxplots


def gen_boxplot_data(res):
    idx_ok = np.where(res[0] > 25)[0]  # exclude 3 tasks with trivial sig
    power_change_notip = ((res[0] - res[1]) / res[1]) * 100
    return [power_change_notip[idx_ok]]


data_a = gen_boxplot_data(res_01)
data_b = gen_boxplot_data(res_02)
data_c = gen_boxplot_data(res_03)

ticks = ['Notip with kmin vs pARI']


def set_box_color(bp, color):
    plt.setp(bp['boxes'], color=color)
    plt.setp(bp['whiskers'], color=color)
    plt.setp(bp['caps'], color=color)
    plt.setp(bp['medians'], color=color)


fig, ax = plt.subplots(figsize=(10, 6))

# Adjust positions to center the middle box plot
pos_center = np.array([0])
pos0 = pos_center - 0.6
pos1 = pos_center
pos2 = pos_center + 0.6

# Gather all points for dynamic axis adjustment
all_points = np.concatenate([data_a[0], data_b[0], data_c[0]])

# Add dots to boxplots
for nb in range(len(data_a)):
    for i in range(len(data_a[nb])):
        y = data_a[nb][i]
        x = np.random.normal(pos0[nb], 0.1)
        ax.scatter(x, y, c='#66c2a4', alpha=0.75, marker='v')

for nb in range(len(data_b)):
    for i in range(len(data_b[nb])):
        y = data_b[nb][i]
        x = np.random.normal(pos1[nb], 0.1)
        ax.scatter(x, y, c='#238b45', alpha=0.75, marker='D')

for nb in range(len(data_c)):
    for i in range(len(data_c[nb])):
        y = data_c[nb][i]
        x = np.random.normal(pos2[nb], 0.1)
        ax.scatter(x, y, c='#00441b', alpha=0.75, marker='p')

# Create the boxplots
bpl = ax.boxplot(data_a, positions=pos0, sym='', widths=0.3)
bpr = ax.boxplot(data_b, positions=pos1, sym='', widths=0.3)
bpc = ax.boxplot(data_c, positions=pos2, sym='', widths=0.3)

set_box_color(bpl, '#66c2a4')  # colors are from http://colorbrewer2.org/
set_box_color(bpr, '#238b45')
set_box_color(bpc, '#00441b')

# Draw temporary red and blue lines and use them to create a legend
ax.scatter([], [], c='#66c2a4', marker='v', label=r'$FDP \leq 0.05$')
ax.scatter([], [], c='#238b45', marker='D', label=r'$FDP \leq 0.1$')
ax.scatter([], [], c='#00441b', marker='p', label=r'$FDP \leq 0.2$')
ax.legend(loc='upper right', prop={'size': 8.5})

# Set axis limits based on the data points
ax.set_ylim(-20, +20)
ax.set_xlim(-1, 1)

ax.set_xticks(pos_center)
ax.set_xticklabels(ticks)
ax.set_ylabel('Detection rate variation (%)')
ax.hlines(0, xmin=-1, xmax=1, color='black')
ax.set_title(r'Detection rate variation for $\alpha = 0.05$ and various FDPs')
plt.tight_layout()
plt.subplots_adjust(left=0.1, right=0.9, top=0.9, bottom=0.1)
plt.savefig('/home/onyxia/work/Notip/figures/comparison_Notip_pARI.png')
plt.show()