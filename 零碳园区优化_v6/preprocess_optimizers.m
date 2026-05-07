function preprocess_optimizers(data, rhoPQ)
%PREPROCESS_OPTIMIZERS
% Explicitly compile and cache the optimizer models before solving.
% This function first clears stale optimizer handles because yalmip('clear')
% and code replacement can invalidate persistent optimizer objects.

if nargin < 2 || isempty(rhoPQ)
    rhoPQ = 3*ones(data.N,1);
end

% Always clear stale caches before building new optimizer handles.
try, solve_local_subproblem('clear_cache'); catch, end
try, feeder_projection('clear_cache'); catch, end
try, yalmip('clear'); catch, end

N = data.N;
T = data.T;
zP0 = zeros(N,T);
zQ0 = zeros(N,T);
lambdaP0 = zeros(1,T);
lambdaQ0 = zeros(1,T);

for i = 1:N
    p = build_local_params(data, i, zP0, zQ0, lambdaP0, lambdaQ0, rhoPQ(i));
    solve_local_subproblem('prebuild', p);
end

feeder_projection('prebuild', data, rhoPQ);
end
