function preprocess_optimizers(data, rhoPQ, resetFirst)
%PREPROCESS_OPTIMIZERS Explicitly compile and cache ADMM optimizer models.
%
% P1 acceleration:
%   - Do NOT clear optimizer caches every time this function is called.
%   - Repeated calls from main_run_comparison.m and main_year.m now only
%     prebuild missing structural cache entries, so scenarios with the same
%     model structure reuse already compiled YALMIP optimizer objects.
%
% Usage:
%   preprocess_optimizers(data, rhoPQ)          % reuse caches
%   preprocess_optimizers(data, rhoPQ, true)    % clear and rebuild caches

if nargin < 2 || isempty(rhoPQ)
    rhoPQ = 3*ones(data.N,1);
end
if nargin < 3 || isempty(resetFirst)
    resetFirst = false;
end

if isscalar(rhoPQ)
    rhoPQ = rhoPQ*ones(data.N,1);
else
    rhoPQ = rhoPQ(:);
end

if resetFirst
    try, solve_local_subproblem('clear_cache'); catch, end
    try, feeder_projection('clear_cache'); catch, end
    try, yalmip('clear'); catch, end
end

N = data.N;
T = data.T;
zP0 = zeros(N,T);
zQ0 = zeros(N,T);
lambdaP0 = zeros(1,T);
lambdaQ0 = zeros(1,T);
zC0 = zeros(N,T);
lambdaC0 = zeros(1,T);

for i = 1:N
    p = build_local_params(data, i, zP0, zQ0, lambdaP0, lambdaQ0, rhoPQ(i), zC0, lambdaC0, rhoPQ(i));
    solve_local_subproblem('prebuild', p);
end

feeder_projection('prebuild', data, rhoPQ);
end
