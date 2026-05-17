function preprocess_optimizers(data, rhoPQ, rhoC, resetFirst)
%PREPROCESS_OPTIMIZERS Explicitly compile/cache ADMM optimization models.
%
% Updated rhoPQ/rhoC version:
%   - Local community subproblems are still prebuilt as YALMIP optimizers.
%   - The feeder projection is matrixized for direct Gurobi QP by default.
%   - P/Q consensus and carbon consensus can use different penalties.
%
% Usage:
%   preprocess_optimizers(data, rhoPQ, rhoC)          % required: pass rhoPQ and rhoC vectors
%   preprocess_optimizers(data, rhoPQ, rhoC, true)    % clear and rebuild caches
%
% Backward compatible:
%   preprocess_optimizers(data, rhoPQ, true)          % old style reset flag

N = data.N;

% Backward compatibility: third argument used to be resetFirst.
if nargin >= 3 && islogical(rhoC) && isscalar(rhoC)
    resetFirst = rhoC;
    rhoC = [];
elseif nargin < 4 || isempty(resetFirst)
    resetFirst = false;
end

rhoPQ = normalize_rho_vector_local(rhoPQ, N, 'rhoPQ');
rhoC  = normalize_rho_vector_local(rhoC,  N, 'rhoC');

useGurobiFeeder = true;
if isfield(data, 'useGurobiFeederProjection') && ~isempty(data.useGurobiFeederProjection)
    useGurobiFeeder = logical(data.useGurobiFeederProjection);
end

if resetFirst
    try, solve_local_subproblem('clear_cache'); catch, end
    try, feeder_projection('clear_cache'); catch, end
    try, feeder_projection_gurobi('clear_cache'); catch, end
    try, yalmip('clear'); catch, end
end

T = data.T;
zP0 = zeros(N,T);
zQ0 = zeros(N,T);
lambdaP0 = zeros(1,T);
lambdaQ0 = zeros(1,T);
zC0 = zeros(N,T);
lambdaC0 = zeros(1,T);

for i = 1:N
    p = build_local_params(data, i, zP0, zQ0, lambdaP0, lambdaQ0, rhoPQ(i), zC0, lambdaC0, rhoC(i));
    solve_local_subproblem('prebuild', p);
end

if useGurobiFeeder
    feeder_projection_gurobi('prebuild', data);
else
    feeder_projection('prebuild', data, rhoPQ);
end
end

function val = get_data_field_local(s, name, defaultVal)
if isfield(s, name) && ~isempty(s.(name))
    val = s.(name);
else
    val = defaultVal;
end
end

function rhoVec = normalize_rho_vector_local(raw, N, name)
if isempty(raw)
    error('%s cannot be empty.', name);
end
if isscalar(raw)
    rhoVec = raw*ones(N,1);
else
    rhoVec = raw(:);
end
if numel(rhoVec) ~= N
    error('%s must be scalar or %d-element vector.', name, N);
end
if any(~isfinite(rhoVec)) || any(rhoVec <= 0)
    error('%s must contain positive finite values.', name);
end
end
