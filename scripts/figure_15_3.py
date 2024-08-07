import matplotlib.pyplot as plt
import numpy as np
from tqdm import tqdm

import os
import sys
from nilearn.datasets import fetch_neurovault


script_path = os.path.dirname(__file__)
fig_path_ = os.path.abspath(os.path.join(script_path, os.pardir))
fig_path = os.path.join(fig_path_, 'figures')

sys.path.append(script_path)

fetch_neurovault(max_images=np.infty, mode='download_new', collection_id=1952)

seed = 42
task_id = 0
task_nb = 36
p = 51199
k_max = 1000

TDPs = [0.95, 0.9, 0.8]
alphas = [0.05, 0.1, 0.2]

k_mins = [0, 1, 3, 9, 27, 45, 81, 100]

fig, axs = plt.subplots(3, 3, figsize=(12, 12))
fig.tight_layout()
plt.subplots_adjust(left=0.1, bottom=0.1, right=None,
                    top=None, wspace=0.4, hspace=0.4)

for i in range(len(alphas)):
    for j in range(len(TDPs)):
        alpha = alphas[i]
        TDP = TDPs[j]
        curves_tot = np.zeros((task_nb, len(k_mins), 2))
        for task_id in tqdm(range(task_nb)):
            curve = np.load(os.path.join(fig_path, "fig10/kmin_curve_task%d_tdp%.2f_alpha%.2f.npy" % (task_id, TDP, alpha)))
            if curve[0][0] > 25:
                curves_tot[task_id] = curve
                # curves_tot[task_id] = curve / (curve[0][0] - 1)
                # Normalise by ARI
        compt = 0
        for task_id in tqdm(range(task_nb)):
            curve = np.load(os.path.join(fig_path, "fig10/kmin_curve_task%d_tdp%.2f_alpha%.2f.npy" % (task_id, TDP, alpha)))
            if curve[0][0] <= 25:
                curves_tot = np.delete(curves_tot, task_id - compt, axis=0)
                compt += 1

        mean_ = curves_tot.mean(axis=0)
        # mean_ = np.median(curves_tot, axis=0)

        err_mat = np.zeros((2, len(k_mins)))
        for method in range(2):
            for l in range(len(k_mins)):
                current = curves_tot[:, l, method]
                err = current.std() * np.sqrt(1/len(current) +
                                              (current - current.mean())**2 / np.sum((current - current.mean())**2))
                err_mat[method][l] = np.quantile(err, 0.05)

        pARI_bounds, learned_bounds = mean_[:, 0], mean_[:, 1]
        axs[i][j].plot(k_mins, mean_[:, 0], label='Calibrated Shifted Simes (pARI)',
                       color='red')
        axs[i][j].plot(k_mins, mean_[:, 1], label='Learned template (Notip)',
                       color='blue')
        axs[i][j].fill_between(k_mins, mean_[:, 0] - err_mat[0], mean_[:, 0] + err_mat[0], alpha=0.2, color='red')
        axs[i][j].fill_between(k_mins, mean_[:, 1] - err_mat[1], mean_[:, 1] + err_mat[1], alpha=0.2, color='blue')
        if i == 2:
            axs[i][j].set(xlabel='k_min')
        if j == 0:
            axs[i][j].set(ylabel='Region size')
        axs[i][j].legend()
        axs[i][j].set_title(r'$\alpha = %.2f, FDP \leq %.2f$' % (alpha, 1 - TDP))

plt.savefig(os.path.join(fig_path, 'figure_15.png'))
plt.show()
