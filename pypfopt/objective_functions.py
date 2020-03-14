"""
The ``objective_functions`` module provides optimisation objectives, including the actual
objective functions called by the ``EfficientFrontier`` object's optimisation methods.
These methods are primarily designed for internal use during optimisation (via
scipy.optimize), and each requires a certain signature (which is why they have not been
factored into a class). For obvious reasons, any objective function must accept ``weights``
as an argument, and must also have at least one of ``expected_returns`` or ``cov_matrix``.

Because scipy.optimize only minimises, any objectives that we want to maximise must be
made negative.

Currently implemented:

- negative mean return
- (regularised) negative Sharpe ratio
- (regularised) volatility
- negative quadratic utility
- negative CVaR (expected shortfall). Caveat emptor: this is very buggy.
"""

import numpy as np
import cvxpy as cp
import pandas as pd


def _objective_value(w, obj):
    """
    Helper method to return either the value of the objective function
    or the objective function as a cvxpy object depending on whether
    w is a cvxpy variable or np array.

    :param w: weights
    :type w: np.ndarray OR cp.Variable
    :param obj: objective function expression
    :type obj: cp.Expression
    :return: value of the objective function OR objective function expression
    :rtype: float OR cp.Expression
    """
    if isinstance(w, np.ndarray):
        if np.isscalar(obj.value):
            return obj.value
        else:
            return obj.value.item()
    else:
        return obj


def portfolio_variance(w, cov_matrix):
    if isinstance(w, pd.Series):
        w = w.values

    variance = cp.quad_form(w, cov_matrix)
    return _objective_value(w, variance)


def L2_reg(w, gamma=1):
    if isinstance(w, pd.Series):
        w = w.values
    L2_reg = gamma * cp.sum_squares(w)
    return _objective_value(w, L2_reg)


def negative_mean_return(weights, expected_returns):
    """
    Calculate the negative mean return of a portfolio

    :param weights: asset weights of the portfolio
    :type weights: np.ndarray
    :param expected_returns: expected return of each asset
    :type expected_returns: pd.Series
    :return: negative mean return
    :rtype: float
    """
    return -weights.dot(expected_returns)


def negative_sharpe(
    weights, expected_returns, cov_matrix, gamma=0, risk_free_rate=0.02
):
    """
    Calculate the negative Sharpe ratio of a portfolio

    :param weights: asset weights of the portfolio
    :type weights: np.ndarray
    :param expected_returns: expected return of each asset
    :type expected_returns: pd.Series
    :param cov_matrix: the covariance matrix of asset returns
    :type cov_matrix: pd.DataFrame
    :param gamma: L2 regularisation parameter, defaults to 0. Increase if you want more
                    non-negligible weights
    :type gamma: float, optional
    :param risk_free_rate: risk-free rate of borrowing/lending, defaults to 0.02.
                           The period of the risk-free rate should correspond to the
                           frequency of expected returns.
    :type risk_free_rate: float, optional
    :return: negative Sharpe ratio
    :rtype: float
    """
    mu = weights.dot(expected_returns)
    sigma = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights.T)))
    L2_reg = gamma * (weights ** 2).sum()
    return -(mu - risk_free_rate) / sigma + L2_reg


def volatility(weights, cov_matrix, gamma=0):
    """
    Calculate the volatility of a portfolio. This is actually a misnomer because
    the function returns variance, which is technically the correct objective
    function when minimising volatility.

    :param weights: asset weights of the portfolio
    :type weights: np.ndarray
    :param cov_matrix: the covariance matrix of asset returns
    :type cov_matrix: pd.DataFrame
    :param gamma: L2 regularisation parameter, defaults to 0. Increase if you want more
                  non-negligible weights
    :type gamma: float, optional
    :return: portfolio variance
    :rtype: float
    """
    L2_reg = gamma * (weights ** 2).sum()
    portfolio_volatility = np.dot(weights.T, np.dot(cov_matrix, weights))
    return portfolio_volatility + L2_reg


def negative_quadratic_utility(
    weights, expected_returns, cov_matrix, risk_aversion, gamma=0
):
    """
    Calculate the (negative) quadratic utility of a portfolio.

    :param weights: asset weights of the portfolio
    :type weights: np.ndarray
    :param expected_returns: expected return of each asset
    :type expected_returns: pd.Series
    :param cov_matrix: the covariance matrix of asset returns
    :type cov_matrix: pd.DataFrame
    :param gamma: L2 regularisation parameter, defaults to 0. Increase if you want more
                    non-negligible weights
    :type gamma: float, optional
    """
    L2_reg = gamma * (weights ** 2).sum()
    mu = weights.dot(expected_returns)
    portfolio_volatility = np.dot(weights.T, np.dot(cov_matrix, weights))
    return -(mu - 0.5 * risk_aversion * portfolio_volatility) + L2_reg


# def negative_cvar(weights, returns, s=10000, beta=0.95, random_state=None):
#     """
#     Calculate the negative CVaR. Though we want the "min CVaR portfolio", we
#     actually need to maximise the expected return of the worst q% cases, thus
#     we need this value to be negative.

#     :param weights: asset weights of the portfolio
#     :type weights: np.ndarray
#     :param returns: asset returns
#     :type returns: pd.DataFrame or np.ndarray
#     :param s: number of bootstrap draws, defaults to 10000
#     :type s: int, optional
#     :param beta: "significance level" (i. 1 - q), defaults to 0.95
#     :type beta: float, optional
#     :param random_state: seed for random sampling, defaults to None
#     :type random_state: int, optional
#     :return: negative CVaR
#     :rtype: float
#     """
#     import scipy.stats
#     np.random.seed(seed=random_state)
#     # Calcualte the returns given the weights
#     portfolio_returns = (weights * returns).sum(axis=1)
#     # Sample from the historical distribution
#     dist = scipy.stats.gaussian_kde(portfolio_returns)
#     sample = dist.resample(s)
#     # Calculate the value at risk
#     var = portfolio_returns.quantile(1 - beta)
#     # Mean of all losses worse than the value at risk
#     return -sample[sample < var].mean()
