""" Parameter estimation classes

@author: Jerker Nordh
"""
from pyparticleest.simulator import Simulator
from pyparticleest.filter import sample
import numpy
import scipy.optimize
import matplotlib.pyplot as plt


class ParamEstimation(Simulator):
    """
    Extension of the Simulator class to iterative perform particle smoothing
    combined with a gradienst search algorithms for maximizing the likelihood
    of the parameter estimates
    """

    def maximize(self, param0, num_part, num_traj, max_iter=1000, tol=0.001,
                 callback=None, callback_sim=None, meas_first=False,
                 filter='pf', smoother='full', smoother_options=None):
        """
        Find the maximum likelihood estimate of the paremeters using an
        EM-algorihms combined with a gradient search algorithms

        Args:
         - param0 (array-like): Initial parameter estimate
         - num_part (int/array-like): Number of particle to use in the forward filter
           if array each iteration takes the next element from the array when setting
           up the filter
         - num_traj (int/array-like): Number of smoothed trajectories to create
           if array each iteration takes the next element from the array when setting
           up the smoother
         - max_iter (int): Max number of EM-iterations to perform
         - tol (float): When the different in loglikelihood between two iterations
           is less that his value the algorithm is terminated
         - callback (function): Callback after each EM-iteration with new estimate
         - callback_sim (function): Callback after each simulation
         - bounds (array-like): Hard bounds on parameter estimates
         - meas_first (bool): If true, first measurement occurs before the first
           time update
         - smoother (string): Which particle smoother to use
         - smoother_options (dict): Extra options for the smoother
         - analytic_gradient (bool): Use analytic gradient (requires that the model
           implements ParamEstInterface_GradientSearch)
        """

        params_local = numpy.copy(param0)
        Q = -numpy.Inf
        for _i in xrange(max_iter):
            Q_old = Q
            self.set_params(params_local)
            if (numpy.isscalar(num_part)):
                nump = num_part
            else:
                if (_i < len(num_part)):
                    nump = num_part[_i]
                else:
                    nump = num_part[-1]
            if (numpy.isscalar(num_traj)):
                numt = num_traj
            else:
                if (_i < len(num_traj)):
                    numt = num_traj[_i]
                else:
                    numt = num_traj[-1]

            self.simulate(nump, numt, filter=filter, smoother=smoother,
                          smoother_options=smoother_options, meas_first=meas_first)
            if (callback_sim != None):
                callback_sim(self)

            params_local = self.model.maximize(self.straj)
            # res = scipy.optimize.minimize(fun=fval, x0=params, method='nelder-mead', jac=fgrad)

            # FIXME: Q value not accesible (not needed?)
            # Should the callback define when we terminate the EM-algorithm?
            # (Q, Q_grad) = fval(params_local)
            #Q = fval(params_local)
            #Q = -Q
            # Q_grad = -Q_grad
            if (callback != None):
                callback(params=params_local, Q=-numpy.Inf) #, Q=Q)
#            if (numpy.abs(Q - Q_old) < tol):
#                break
        #return (params_local, Q)
        return (params_local, -numpy.Inf)

def alpha_gen(it):
    offset = 100
    if (it <= offset):
        return 1
    else :
        return (it - offset) ** (-0.51)

class ParamEstimationSAEM(Simulator):
    """
    Extension of the Simulator class to iterative perform particle smoothing
    combined with a gradienst search algorithms for maximizing the likelihood
    of the parameter estimates
    """

    def maximize(self, param0, num_part, num_traj, max_iter=1000, tol=0.001,
                 callback=None, callback_sim=None, meas_first=False,
                 filter='pf', filter_options=None,
                 smoother='full', smoother_options=None,
                 alpha_gen=alpha_gen):
        """
        Find the maximum likelihood estimate of the paremeters using an
        EM-algorihms combined with a gradient search algorithms

        Args:
         - param0 (array-like): Initial parameter estimate
         - num_part (int/array-like): Number of particle to use in the forward filter
           if array each iteration takes the next element from the array when setting
           up the filter
         - num_traj (int/array-like): Number of smoothed trajectories to create
           if array each iteration takes the next element from the array when setting
           up the smoother
         - max_iter (int): Max number of EM-iterations to perform
         - tol (float): When the different in loglikelihood between two iterations
           is less that his value the algorithm is terminated
         - callback (function): Callback after each EM-iteration with new estimate
         - callback_sim (function): Callback after each simulation
         - bounds (array-like): Hard bounds on parameter estimates
         - meas_first (bool): If true, first measurement occurs before the first
           time update
         - smoother (string): Which particle smoother to use
         - smoother_options (dict): Extra options for the smoother
         - analytic_gradient (bool): Use analytic gradient (requires that the model
           implements ParamEstInterface_GradientSearch)
        """

        params_local = numpy.copy(param0)
        alltrajs = None
        weights = None

        for i in xrange(max_iter):
            self.set_params(params_local)

            if (numpy.isscalar(num_part)):
                nump = num_part
            else:
                if (i < len(num_part)):
                    nump = num_part[i]
                else:
                    nump = num_part[-1]
            if (numpy.isscalar(num_traj)):
                numt = num_traj
            else:
                if (i < len(num_traj)):
                    numt = num_traj[i]
                else:
                    numt = num_traj[-1]

            self.simulate(nump, numt, filter=filter, filter_options=filter_options,
                          smoother=smoother, smoother_options=smoother_options,
                          meas_first=meas_first)

            w = numpy.ones((numt,)) / numt
            newtrajs = numpy.copy(self.straj.traj)
            alpha = alpha_gen(i)
            if (weights == None):
                weights = w
            else:
                weights = numpy.concatenate(((1.0 - alpha) * weights, alpha * w))

            if (callback_sim != None):
                callback_sim(self)

            if (alltrajs == None):
                alltrajs = numpy.copy(newtrajs)
            else:
                alltrajs = numpy.concatenate((alltrajs, newtrajs), axis=1)

            zero_ind = (weights == 0.0)
            weights = weights[~zero_ind]
            alltrajs = alltrajs[:, ~zero_ind]
            params_local = self.model.maximize_weighted(self.straj, alltrajs, weights)

            if (callback != None):
                callback(params=params_local, Q=-numpy.Inf) #, Q=Q)
        return (params_local, -numpy.Inf)

class ParamEstimationPSAEM(Simulator):
    """
    Extension of the Simulator class to iterative perform particle smoothing
    combined with a gradienst search algorithms for maximizing the likelihood
    of the parameter estimates
    """

    def maximize(self, param0, num_part, max_iter=1000, tol=0.001,
                 callback=None, callback_sim=None, meas_first=False,
                 filter='cpfas', filter_options=None,
                 alpha_gen=alpha_gen):
        """
        Find the maximum likelihood estimate of the paremeters using an
        EM-algorihms combined with a gradient search algorithms

        Args:
         - param0 (array-like): Initial parameter estimate
         - num_part (int/array-like): Number of particle to use in the forward filter
           if array each iteration takes the next element from the array when setting
           up the filter
         - num_traj (int/array-like): Number of smoothed trajectories to create
           if array each iteration takes the next element from the array when setting
           up the smoother
         - max_iter (int): Max number of EM-iterations to perform
         - tol (float): When the different in loglikelihood between two iterations
           is less that his value the algorithm is terminated
         - callback (function): Callback after each EM-iteration with new estimate
         - callback_sim (function): Callback after each simulation
         - bounds (array-like): Hard bounds on parameter estimates
         - meas_first (bool): If true, first measurement occurs before the first
           time update
         - smoother (string): Which particle smoother to use
         - smoother_options (dict): Extra options for the smoother
         - analytic_gradient (bool): Use analytic gradient (requires that the model
           implements ParamEstInterface_GradientSearch)
        """

        params_local = numpy.copy(param0)
        alltrajs = None
        weights = None

        ind = numpy.asarray(range(num_part), dtype=numpy.int)
        for i in xrange(max_iter):
            self.set_params(params_local)

            self.simulate(num_part, 1, filter=filter, filter_options=filter_options,
                          smoother='ancestor', meas_first=meas_first)

            tmp = self.straj.calculate_ancestors(self.pt, ind)

            T = len(tmp)
            N = tmp[0].pa.part.shape[0]
            D = tmp[0].pa.part.shape[1]

            newtrajs = numpy.empty((T, N, D))

            for t in xrange(T):
                newtrajs[t] = tmp[t].pa.part


            w = numpy.exp(self.pt.traj[-1].pa.w)
            w = numpy.copy(w / numpy.sum(w))

            alpha = alpha_gen(i)
            if (weights == None):
                weights = w
            else:
                weights = numpy.concatenate(((1.0 - alpha) * weights, alpha * w))

            filter_options['cond_traj'] = numpy.copy(self.straj.traj)
            if (callback_sim != None):
                callback_sim(self)

            if (alltrajs == None):
                alltrajs = numpy.copy(newtrajs)
            else:
                alltrajs = numpy.concatenate((alltrajs, newtrajs), axis=1)

            zero_ind = (weights == 0.0)
            weights = weights[~zero_ind]
            alltrajs = alltrajs[:, ~zero_ind]
            params_local = self.model.maximize_weighted(self.straj, alltrajs, weights)

            if (callback != None):
                callback(params=params_local, Q=-numpy.Inf) #, Q=Q)
        return (params_local, -numpy.Inf)

class ParamEstimationPSAEM2(Simulator):
    """
    Extension of the Simulator class to iterative perform particle smoothing
    combined with a gradienst search algorithms for maximizing the likelihood
    of the parameter estimates
    """

    def maximize(self, param0, num_part, max_iter=1000, tol=0.001,
                 callback=None, callback_sim=None, meas_first=False,
                 filter='pf', filter_options=None,
                 smoother='full', smoother_options=None, alpha_gen=alpha_gen):
        """
        Find the maximum likelihood estimate of the paremeters using an
        EM-algorihms combined with a gradient search algorithms

        Args:
         - param0 (array-like): Initial parameter estimate
         - num_part (int/array-like): Number of particle to use in the forward filter
           if array each iteration takes the next element from the array when setting
           up the filter
         - num_traj (int/array-like): Number of smoothed trajectories to create
           if array each iteration takes the next element from the array when setting
           up the smoother
         - max_iter (int): Max number of EM-iterations to perform
         - tol (float): When the different in loglikelihood between two iterations
           is less that his value the algorithm is terminated
         - callback (function): Callback after each EM-iteration with new estimate
         - callback_sim (function): Callback after each simulation
         - bounds (array-like): Hard bounds on parameter estimates
         - meas_first (bool): If true, first measurement occurs before the first
           time update
         - smoother (string): Which particle smoother to use
         - smoother_options (dict): Extra options for the smoother
         - analytic_gradient (bool): Use analytic gradient (requires that the model
           implements ParamEstInterface_GradientSearch)
        """

        params_local = numpy.copy(param0)
        alltrajs = None
        weights = numpy.empty((max_iter * num_part,))

        datalen = 0
        for i in xrange(max_iter):
            self.set_params(params_local)

            self.simulate(num_part, 1, filter=filter, filter_options=filter_options,
                          smoother=smoother, smoother_options=smoother_options,
                          meas_first=meas_first)

            tmp = numpy.copy(self.straj.traj)
            T = len(tmp)
            N = tmp[0].pa.part.shape[0]
            D = tmp[0].pa.part.shape[1]

            newtrajs = numpy.empty((T, N, D))

            for t in xrange(T):
                newtrajs[t] = tmp[t].pa.part

            w = 1.0

            alpha = alpha_gen(i)
            weights[:datalen] *= (1.0 - alpha)
            weights[datalen:datalen + 1] = alpha * w

#            weights[datalen:datalen + 1] = alpha * w

            filter_options['cond_traj'] = numpy.copy(self.straj.traj)
            if (callback_sim != None):
                callback_sim(self)

            if (alltrajs == None):
                alltrajs = numpy.copy(newtrajs)
            else:
                alltrajs = numpy.concatenate((alltrajs[:, :datalen], newtrajs), axis=1)

            datalen += 1

            zero_ind = (weights[:datalen] == 0.0)
            zerolen = numpy.count_nonzero(zero_ind)
            weights[:datalen - zerolen] = weights[:datalen][~zero_ind]
            alltrajs[:, :datalen - zerolen] = alltrajs[:, :datalen][:, ~zero_ind]
            datalen -= zerolen
            params_local = self.model.maximize_weighted(self.straj, alltrajs[:, :datalen], weights[:datalen])
#            params_local = self.model.maximize_weighted(self.straj, alltrajs[:, -1:], numpy.asarray((1.0,)))

            if (callback != None):
                callback(params=params_local, Q=-numpy.Inf) #, Q=Q)
        return (params_local, -numpy.Inf)

class GradPlot():
    def __init__(self, params, vals, diff):
        self.params = params
        self.vals = vals
        self.diff = diff

    def plot(self, fig_id):
        fig = plt.figure(fig_id)
        fig.clf()
        plt.plot(self.params, self.vals)
        if (self.diff != None):
            for k in range(len(self.params)):
                if (k % 10 == 1):
                    self.draw_gradient(self.params[k], self.vals[k], self.params[k] - self.params[k - 1], self.diff[k])


    def draw_gradient(self, x, y, dx, dydx):
        plt.plot((x - dx, x + dx), (y - dydx * dx, y + dydx * dx), 'r')


class GradientTest(ParamEstimation):

    def test(self, param_id, param_vals, num=100, nums=1, analytic_grad=True):
        self.simulate(num_part=num, num_traj=nums)
        param_steps = len(param_vals)
        logpy = numpy.zeros((param_steps,))
        logpxn = numpy.zeros((param_steps,))
        logpx0 = numpy.zeros((param_steps,))
        if (analytic_grad):
            grad_logpy = numpy.zeros((param_steps, len(self.params)))
            grad_logpxn = numpy.zeros((param_steps, len(self.params)))
            grad_logpx0 = numpy.zeros((param_steps, len(self.params)))
        for k in range(param_steps):
            tmp = numpy.copy(self.params)
            tmp[param_id] = param_vals[k]
            self.set_params(tmp)
            logpy[k] = self.model.eval_logp_y_fulltraj(self.straj,
                                                       self.straj.y,
                                                       self.straj.t)
            logpxn[k] = self.model.eval_logp_xnext_fulltraj(self.straj,
                                                             self.straj.u,
                                                             self.straj.t)
            tmp = self.model.eval_logp_x0(self.straj.traj[0],
                                          self.straj.t[0])
            logpx0[k] = numpy.mean(tmp)

            if (analytic_grad):
                (_, grad_logp_y) = self.model.eval_logp_y_val_grad_fulltraj(self.straj,
                                                                             self.straj.y,
                                                                             self.straj.t)
                (_, grad_logp_xnext) = self.model.eval_logp_xnext_val_grad_fulltraj(self.straj,
                                                                                     self.straj.u,
                                                                                     self.straj.t)
                (tmp1, tmp2) = self.model.eval_logp_x0_val_grad(self.straj.traj[0],
                                                                self.straj.t[0])
                (_, grad_logp_x0) = (numpy.mean(tmp1), numpy.mean(tmp2))

                grad_logpy[k] = grad_logp_y
                grad_logpxn[k] = grad_logp_xnext
                grad_logpx0[k] = grad_logp_x0
                self.plot_y = GradPlot(param_vals, logpy, grad_logpy[:, param_id])
                self.plot_xn = GradPlot(param_vals, logpxn, grad_logpxn[:, param_id])
                self.plot_x0 = GradPlot(param_vals, logpx0, grad_logpx0[:, param_id])
            else:
                self.plot_y = GradPlot(param_vals, logpy, None)
                self.plot_xn = GradPlot(param_vals, logpxn, None)
                self.plot_x0 = GradPlot(param_vals, logpx0, None)



