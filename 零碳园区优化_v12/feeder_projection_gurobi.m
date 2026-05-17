function [zP, zQ, feeder] = feeder_projection_gurobi(varargin)
%FEEDER_PROJECTION_GUROBI Matrixized Gurobi QP feeder P/Q projection.
%
% Usage:
%   [zP,zQ,feeder] = feeder_projection_gurobi(targetP,targetQ,data,rhoPQ)
%   [zP,zQ,feeder] = feeder_projection_gurobi(targetP,targetQ,data,rhoPQ,base)
%   feeder_projection_gurobi('prebuild', data)
%   feeder_projection_gurobi('clear_cache')
%
% The QP solved is:
%   min 0.5*rho_i*(zP_i-targetP_i)^2 + 0.5*rho_i*(zQ_i-targetQ_i)^2
% subject to the linear DistFlow feeder feasible set.
%
% Gurobi MATLAB's model.Q uses x'*Q*x + obj'*x, so the diagonal Q entries
% for zP/zQ are set to rho_i/2.

persistent CACHE
if isempty(CACHE)
    CACHE = containers.Map('KeyType','char','ValueType','any');
end

if nargin >= 1 && (ischar(varargin{1}) || isstring(varargin{1}))
    cmd = lower(char(varargin{1}));
    switch cmd
        case {'reset','clear_cache'}
            CACHE = containers.Map('KeyType','char','ValueType','any');
            zP = []; zQ = []; feeder = struct();
            return;
        case 'prebuild'
            if nargin < 2
                error('feeder_projection_gurobi(''prebuild'', data) requires data.');
            end
            data = varargin{2};
            base = build_feeder_qp_base(data);
            CACHE(base.cacheKey) = base;
            zP = []; zQ = []; feeder = struct();
            return;
        otherwise
            error('Unknown command: %s', cmd);
    end
end

if nargin ~= 4 && nargin ~= 5
    error('feeder_projection_gurobi expects targetP, targetQ, data, rhoPQ, and optional base.');
end

targetP = varargin{1};
targetQ = varargin{2};
data    = varargin{3};
rhoPQ   = varargin{4};

if nargin == 5 && ~isempty(varargin{5})
    base = varargin{5};
else
    tmp = build_feeder_qp_base(data);
    key = tmp.cacheKey;
    if isKey(CACHE, key)
        base = CACHE(key);
    else
        base = tmp;
        CACHE(key) = base;
    end
end

N = base.N;
T = base.T;
L = base.L;
B = base.B;
if ~isequal(size(targetP), [N,T]) || ~isequal(size(targetQ), [N,T])
    error('targetP/targetQ size mismatch. Expected %d-by-%d.', N, T);
end

if isscalar(rhoPQ)
    rhoVec = rhoPQ*ones(N,1);
else
    rhoVec = rhoPQ(:);
end
if numel(rhoVec) ~= N
    error('rhoPQ must be scalar or %d-element vector.', N);
end

rhoMat = repmat(rhoVec, 1, T);

model = base.model;
qdiag = zeros(base.nvar,1);
qdiag(base.idx.zP(:)) = 0.5*rhoMat(:);
qdiag(base.idx.zQ(:)) = 0.5*rhoMat(:);
model.Q = sparse(1:base.nvar, 1:base.nvar, qdiag, base.nvar, base.nvar);

obj = zeros(base.nvar,1);
obj(base.idx.zP(:)) = -rhoMat(:).*targetP(:);
obj(base.idx.zQ(:)) = -rhoMat(:).*targetQ(:);
model.obj = obj;

params = struct();
params.OutputFlag = 0;
params.TimeLimit = get_data_field_local(data, 'feederGurobiTimeLimit', 60);
if isfield(data, 'gurobiThreads') && ~isempty(data.gurobiThreads)
    params.Threads = data.gurobiThreads;
end
if isfield(data, 'gurobiMIPGap') && ~isempty(data.gurobiMIPGap)
    params.MIPGap = data.gurobiMIPGap;
end

result = gurobi(model, params);
status = upper(char(result.status));
if ~isfield(result, 'x') || isempty(result.x)
    error('Gurobi feeder projection failed without a primal solution. Status: %s.', result.status);
end
if ~ismember(status, {'OPTIMAL','SUBOPTIMAL','TIME_LIMIT'})
    error('Gurobi feeder projection failed. Status: %s.', result.status);
end

x = result.x;
zP = reshape(x(base.idx.zP(:)), N, T);
zQ = reshape(x(base.idx.zQ(:)), N, T);
Pij = reshape(x(base.idx.Pij(:)), L, T);
Qij = reshape(x(base.idx.Qij(:)), L, T);
V   = reshape(x(base.idx.V(:)), B, T);

feeder = struct();
feeder.Pij = Pij;
feeder.Qij = Qij;
feeder.V = V;
feeder.zP = zP;
feeder.zQ = zQ;
feeder.status = result.status;
if isfield(result, 'objval')
    feeder.projObj = result.objval;
end
feeder.solver = 'gurobi-direct-qp';
end

function val = get_data_field_local(s, name, defaultVal)
if isfield(s, name) && ~isempty(s.(name))
    val = s.(name);
else
    val = defaultVal;
end
end
