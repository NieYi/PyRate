'''
Pixel-by-pixel linear rate (velocity) estimation using iterative weighted
least-squares method.

Based on original Matlab code by Hua Wang and Juliet Biggs, and Matlab 'lscov'
function.

.. codeauthor: Matt Garthwaite, GA
'''

from scipy.linalg import solve, cholesky, qr, inv
from numpy import nan, isnan, sqrt, diag, delete, ones, array, nonzero, float32

def linear_rate(ifgs, vcm, pthr, nsig, maxsig, mst=None):
    '''
    Pixel-by-pixel linear rate (velocity) estimation using iterative weighted least-squares method.

    :param ifgs: Sequence of ifg objs from which to extract observations
    :param vcm: Derived positive definite temporal variance covariance matrix
    :param pthr: Pixel threshold; minimum number of coherent observations for a pixel
    :param nsig: n-sigma ratio used to threshold 'model minus observation' residuals
    :param maxsig: Threshold for maximum allowable standard error
    :param mst: Pixel-wise matrix describing the minimum spanning tree network
    '''

    rows, cols = ifgs[0].phase_data.shape
    nifgs = len(ifgs)

    # make 3D block of observations
    obs = array([x.phase_data for x in ifgs])
    span = array([[x.time_span for x in ifgs]])

    # Update MST in case additional NaNs generated by APS filtering
    if mst is not None:
        mst[isnan(obs)] = 0
    else: # dummy mst if none is paased in
        mst = ones((nifgs, rows, cols))

    # preallocate NaN arrays
    error = ones([rows, cols], dtype=float32) * nan
    rate = ones([rows, cols], dtype=float32) * nan
    samples = ones([rows, cols], dtype=float32) * nan

    # pixel-by-pixel calculation. nested loops to loop over the 2 image dimensions
    for i in xrange(rows):
        # This is for providing verbose progress status...
        #if mod(i,50)==0:
            #print("calculating linear rate for the '%d'/'%d' line" % i,rows)

        for j in xrange(cols):
            # find the indices of independent ifgs for given pixel from MST
            ind = nonzero(mst[:, i, j] == 1)[0]
            print ind

            # iterative loop to calculate 'robust' velocity for pixel

            while len(ind) >= pthr:
                print 'here in while'

                # make vector of selected ifg observations
                ifgv = obs[:, i, j][ind]
                ifgv = ifgv.reshape(1, len(ifgv))

                # form design matrix from appropriate ifg time spans
                B = span[:, ind]

                # Subset of full VCM matrix for selected observations
                V = vcm[:, ind][ind, :] # Is this pulling out a subset of vcm based on mst?

                # Get the lower triangle cholesky decomposition. V must be positive definite (symmetrical and square)
                T = cholesky(V, 1)

                # Incorporate inverse of VCM into the design matrix and observations vector
                A = solve(T, B.transpose())
                b = solve(T, ifgv.transpose())

                # Factor the design matrix, incorporate covariances or weights into the
                # system of equations, and transform the response vector.
                Q, R = qr(A, mode='economic')
                z = Q.conj().transpose().dot(b)

                # Compute the Lstsq coefficient for the velocity
                v = solve(R, z)

                # Compute the model errors; added by Hua Wang, 12/12/2011
                err1 = inv(V).dot(B.conj().transpose())
                err2 = B.dot(err1)
                err = sqrt(diag(inv(err2)))
                print "xxxxxxxxxxxxxxxxxxxxxxxxxx===========>", err

                # Compute the residuals (model minus observations)
                r = (B * v) - ifgv

                # determine the ratio of residuals and apriori variances (Danish method)
                w = cholesky( inv(V) )
                wr = abs(w * r.transpose())

                # test if maximum ratio is greater than user threshold.
                maxr = diag(wr).max()
                maxi = nonzero(wr == maxr)[0][0]

                if maxr > nsig:
                    # if yes, discard and re-do the calculation.
                    ind = delete(ind, maxi)
                else:
                    #if no save estimate, exit the while loop and go to next pixel
                    rate[i, j] = v
                    error[i, j] = err
                    samples[i, j] = ifgv[0].shape[0]
                    break

    # overwrite the data whose error is larger than the maximum sigma user threshold
    rate[error > maxsig] = nan
    error[error > maxsig] = nan
    samples[error > maxsig] = nan

    return rate, error, samples
