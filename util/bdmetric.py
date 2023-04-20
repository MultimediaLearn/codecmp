import math
import sys
import numpy as np
import scipy.interpolate

# git repo
# https://github.com/Anserw/Bjontegaard_metric/blob/master/bjontegaard_metric.py
# 排序，码率从高到低
# print 'Sample 1'
# R1 = np.array([686.76, 309.58, 157.11, 85.95])
# PSNR1 = np.array([40.28, 37.18, 34.24, 31.42])
# R2 = np.array([893.34, 407.8, 204.93, 112.75])
# PSNR2 = np.array([40.39, 37.21, 34.17, 31.24])
#
# print 'BD-PSNR: ', BD_PSNR(R1, PSNR1, R2, PSNR2)
# print 'BD-RATE: ', BD_RATE(R1, PSNR1, R2, PSNR2)

# BD_PSNR 和 BD_RATE的区别在于，坐标轴交换
def BD_PSNR(R1, PSNR1, R2, PSNR2, piecewise=0):
    # 必须按照码率从大到小排列
    R1, PSNR1 = (list(t) for t in zip(*sorted(zip(R1, PSNR1), reverse=False)))
    R2, PSNR2 = (list(t) for t in zip(*sorted(zip(R2, PSNR2), reverse=False)))
    lR1 = np.log(R1)
    lR2 = np.log(R2)

    PSNR1 = np.array(PSNR1)
    PSNR2 = np.array(PSNR2)

    # 纵坐标是PSNR
    p1 = np.polyfit(lR1, PSNR1, 3)
    p2 = np.polyfit(lR2, PSNR2, 3)

    # integration interval
    min_int = max(min(lR1), min(lR2))
    max_int = min(max(lR1), max(lR2))

    # find integral
    if piecewise == 0:
        p_int1 = np.polyint(p1)
        p_int2 = np.polyint(p2)

        int1 = np.polyval(p_int1, max_int) - np.polyval(p_int1, min_int)
        int2 = np.polyval(p_int2, max_int) - np.polyval(p_int2, min_int)
    else:
        # See https://chromium.googlesource.com/webm/contributor-guide/+/master/scripts/visual_metrics.py
        lin = np.linspace(min_int, max_int, num=100, retstep=True)
        interval = lin[1]
        samples = lin[0]
        v1 = scipy.interpolate.pchip_interpolate(np.sort(lR1), PSNR1[np.argsort(lR1)], samples)
        v2 = scipy.interpolate.pchip_interpolate(np.sort(lR2), PSNR2[np.argsort(lR2)], samples)
        # Calculate the integral using the trapezoid method on the samples.
        int1 = np.trapz(v1, dx=interval)
        int2 = np.trapz(v2, dx=interval)

    # find avg diff
    avg_diff = (int2-int1)/(max_int-min_int)

    return avg_diff, (R1, PSNR1, R2, PSNR2)


def BD_RATE(R1, PSNR1, R2, PSNR2, piecewise=0):
    # 必须按照码率从大到小排列
    R1, PSNR1 = (list(t) for t in zip(*sorted(zip(R1, PSNR1), reverse=False)))
    R2, PSNR2 = (list(t) for t in zip(*sorted(zip(R2, PSNR2), reverse=False)))
    lR1 = np.log(R1)
    lR2 = np.log(R2)

    # rate method，纵坐标是码率log
    p1 = np.polyfit(PSNR1, lR1, 3)
    p2 = np.polyfit(PSNR2, lR2, 3)

    # integration interval
    min_int = max(min(PSNR1), min(PSNR2))
    max_int = min(max(PSNR1), max(PSNR2))

    # find integral
    if piecewise == 0:
        p_int1 = np.polyint(p1)
        p_int2 = np.polyint(p2)

        int1 = np.polyval(p_int1, max_int) - np.polyval(p_int1, min_int)
        int2 = np.polyval(p_int2, max_int) - np.polyval(p_int2, min_int)
    else:
        lin = np.linspace(min_int, max_int, num=100, retstep=True)
        interval = lin[1]
        samples = lin[0]
        v1 = scipy.interpolate.pchip_interpolate(np.sort(PSNR1), lR1[np.argsort(PSNR1)], samples)
        v2 = scipy.interpolate.pchip_interpolate(np.sort(PSNR2), lR2[np.argsort(PSNR2)], samples)
        # Calculate the integral using the trapezoid method on the samples.
        int1 = np.trapz(v1, dx=interval)
        int2 = np.trapz(v2, dx=interval)

    # find avg diff
    avg_exp_diff = (int2-int1) / (max_int-min_int)
    avg_diff = (np.exp(avg_exp_diff)-1) * 100

    return avg_diff, (R1, PSNR1, R2, PSNR2)

# v265 bdrate caculation
def __pchipend(h1, h2, del1, del2):
    d = ((2 * h1 + h2) * del1 - h1 * del2) / (h1 + h2)
    if (d * del1 < 0):
        d = 0
    elif ((del1 * del2 < 0) and (abs(d) > abs(3 * del1))):
        d = 3 * del1

    return d


def __bdrint(rate, psnr, low, high):
    log_rate = [math.log(rate[3 - i], 10) for i in range(4)]
    log_dist = [psnr[3 - i] for i in range(4)]

    H = [log_dist[i+1] - log_dist[i] for i in range(3)]
    delta = [(log_rate[i + 1] - log_rate[i]) / H[i] for i in range(3)]

    d = [-1 for x in range(4)]
    d[0] = __pchipend(H[0], H[1], delta[0], delta[1])

    for i in range(1, 3):
        d[i] = (3 * H[i - 1] + 3 * H[i]) / ((2 * H[i] + H[i - 1]) / delta[i - 1] + (H[i] + 2 * H[i - 1]) / delta[i])

    d[3] = __pchipend(H[2], H[1], delta[2], delta[1])

    c = [(3 * delta[i] - 2 * d[i] - d[i + 1]) / H[i] for i in range(3)]
    b = [(d[i] - 2 * delta[i] + d[i + 1]) / (H[i] * H[i]) for i in range(3)]

    result = 0
    s0 = 0
    s1 = 0
    for i in range(3):
        s0 = min( max(log_dist[i], low), high )
        s1 = min( max(log_dist[i+1], low), high )

        s0 = s0 - log_dist[i]
        s1 = s1 - log_dist[i]

        if s1 > s0:
            result += (s1 - s0) * log_rate[i]
            result += (s1 * s1 - s0 * s0) * d[i] / 2
            result += (s1 * s1 * s1 - s0 * s0 * s0) * c[i] / 3
            result += (s1 * s1 * s1 * s1 - s0 * s0 * s0 * s0) * b[i] / 4

    return result

def bdrate_v265(rate1, psnr1, rate2, psnr2, piecewise=1):
    if len(rate1) != 4 or len(psnr1) != 4 or len(rate2) != 4 or len(psnr2) != 4:
        print("The input data should have a length of 4.")
        sys.exit(1)
    if piecewise != 1:
        print("bdrate v265 supoort piecewise=1 only")
        sys.exit(1)

    # 必须要求码率从大到小排序，否则计算出错
    rate1, psnr1 = (list(t) for t in zip(*sorted(zip(rate1, psnr1), reverse=True)))
    rate2, psnr2 = (list(t) for t in zip(*sorted(zip(rate2, psnr2), reverse=True)))

    min_psnr = max(min(psnr1), min(psnr2))
    max_psnr = min(max(psnr1), max(psnr2))
    if min(psnr1) == max(psnr1) or min(psnr2) == max(psnr2):
        return 0

    v1 = __bdrint(rate1, psnr1, min_psnr, max_psnr)
    v2 = __bdrint(rate2, psnr2, min_psnr, max_psnr)

    avg = (v2 - v1) / (max_psnr - min_psnr)
    res = math.pow(10, avg) - 1
    if res > 2:
        res = 2
    elif res < -2:
        res = -2

    res *= 100      # 对齐 BDRATE
    return res, (rate1, psnr1, rate2, psnr2)

if __name__ == "__main__":
    import matplotlib.pyplot as plt
    ref_br      = [5012.39, 4012.23, 3014.7, 2014.65]
    ref_metric  = [99.97751, 99.91607, 99.51432, 96.622]
    main_br     = [5096.02, 4000.03, 3067.89, 2054.35]
    main_metric = [99.98146, 99.94996, 99.66744, 97.1181]

    bd, rets = BD_RATE(ref_br, ref_metric, main_br, main_metric, piecewise=1)
    print(bd)
    bd, rets = bdrate_v265(ref_br, ref_metric, main_br, main_metric, piecewise=1)
    print(bd)
    plt.plot(rets[0], rets[1], linestyle="dotted")
    plt.plot(rets[2], rets[3])
    plt.savefig("bdmetric.test.png")
