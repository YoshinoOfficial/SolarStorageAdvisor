function base = build_feeder_qp_base(data)
%BUILD_FEEDER_QP_BASE Build the fixed sparse QP matrices for feeder projection.
%
% This function replaces the YALMIP feeder projection model by a direct
% Gurobi QP base model. It only builds the structural part once:
%   - DistFlow equality constraints
%   - voltage bounds
%   - branch P/Q bounds
%   - substation active-power bounds
%   - zP/zQ bounds
%
% The ADMM target points and rho enter only the quadratic objective and are
% updated in feeder_projection_gurobi.m.

required = {'N','T','B','L','rootBus','branch','out_lines','bus_has_comm','bus_to_comm', ...
    'PbusBase','QbusBase','rline','xline','baseMVA','Vslack','Vmin','Vmax', ...
    'PgridMax','QinjMin','QinjMax','PijMax','QijMax','PsubMax'};
for k = 1:numel(required)
    if ~isfield(data, required{k})
        error('build_feeder_qp_base:MissingField', 'data.%s is required.', required{k});
    end
end

N = data.N;
T = data.T;
B = data.B;
L = data.L;

idx = struct();
off = 0;
idx.zP  = reshape(off+(1:N*T), N, T); off = off + N*T;
idx.zQ  = reshape(off+(1:N*T), N, T); off = off + N*T;
idx.Pij = reshape(off+(1:L*T), L, T); off = off + L*T;
idx.Qij = reshape(off+(1:L*T), L, T); off = off + L*T;
idx.V   = reshape(off+(1:B*T), B, T); off = off + B*T;
nvar = off;

lb = -inf(nvar,1);
ub =  inf(nvar,1);

PgridMax = expand_col_to_matrix(data.PgridMax, N, T);
QinjMin  = expand_col_to_matrix(data.QinjMin,  N, T);
QinjMax  = expand_col_to_matrix(data.QinjMax,  N, T);
PijMax   = expand_col_to_matrix(data.PijMax,   L, T);
QijMax   = expand_col_to_matrix(data.QijMax,   L, T);
Vmin2    = expand_col_to_matrix(data.Vmin(:).^2, B, T);
Vmax2    = expand_col_to_matrix(data.Vmax(:).^2, B, T);

lb(idx.zP(:))  = 0;
ub(idx.zP(:))  = PgridMax(:);
lb(idx.zQ(:))  = QinjMin(:);
ub(idx.zQ(:))  = QinjMax(:);
lb(idx.Pij(:)) = -PijMax(:);
ub(idx.Pij(:)) =  PijMax(:);
lb(idx.Qij(:)) = -QijMax(:);
ub(idx.Qij(:)) =  QijMax(:);
lb(idx.V(:))   = Vmin2(:);
ub(idx.V(:))   = Vmax2(:);

% Sparse matrix triplets.
I = zeros(0,1); J = zeros(0,1); S = zeros(0,1);
rhs = zeros(0,1);
sense = char(zeros(0,1));
row = 0;

    function add_term(col, val)
        I(end+1,1) = row; %#ok<AGROW>
        J(end+1,1) = col; %#ok<AGROW>
        S(end+1,1) = val; %#ok<AGROW>
    end

for t = 1:T
    % Slack voltage equality: V(root,t) = Vslack^2.
    row = row + 1;
    add_term(idx.V(data.rootBus,t), 1);
    rhs(row,1) = data.Vslack^2;
    sense(row,1) = '=';

    for l = 1:L
        from = data.branch(l,1);
        to   = data.branch(l,2);

        % Active DistFlow balance:
        % Pij(l,t) - sum_child Pij(child,t) - zP(comm,t) = PbusBase(to,t)
        row = row + 1;
        add_term(idx.Pij(l,t), 1);
        child_lines = data.out_lines{to};
        for kk = 1:numel(child_lines)
            lp = child_lines(kk);
            add_term(idx.Pij(lp,t), -1);
        end
        if data.bus_has_comm(to)
            ci = data.bus_to_comm(to);
            add_term(idx.zP(ci,t), -1);
        end
        rhs(row,1) = data.PbusBase(to,t);
        sense(row,1) = '=';

        % Reactive DistFlow balance:
        % Qij(l,t) - sum_child Qij(child,t) - zQ(comm,t) = QbusBase(to,t)
        row = row + 1;
        add_term(idx.Qij(l,t), 1);
        for kk = 1:numel(child_lines)
            lp = child_lines(kk);
            add_term(idx.Qij(lp,t), -1);
        end
        if data.bus_has_comm(to)
            ci = data.bus_to_comm(to);
            add_term(idx.zQ(ci,t), -1);
        end
        rhs(row,1) = data.QbusBase(to,t);
        sense(row,1) = '=';

        % Linear DistFlow voltage drop:
        % V(to,t) - V(from,t) + 2*(r/baseMVA*Pij + x/baseMVA*Qij) = 0
        row = row + 1;
        add_term(idx.V(to,t), 1);
        add_term(idx.V(from,t), -1);
        add_term(idx.Pij(l,t), 2*data.rline(l)/data.baseMVA);
        add_term(idx.Qij(l,t), 2*data.xline(l)/data.baseMVA);
        rhs(row,1) = 0;
        sense(row,1) = '=';
    end

    % Substation active power bounds: 0 <= sum_root_out Pij <= PsubMax(t).
    rootOut = data.out_lines{data.rootBus};
    row = row + 1;
    for kk = 1:numel(rootOut)
        add_term(idx.Pij(rootOut(kk),t), 1);
    end
    rhs(row,1) = data.PsubMax(t);
    sense(row,1) = '<';

    row = row + 1;
    for kk = 1:numel(rootOut)
        add_term(idx.Pij(rootOut(kk),t), -1);
    end
    rhs(row,1) = 0;
    sense(row,1) = '<';
end

model = struct();
model.A = sparse(I, J, S, row, nvar);
model.rhs = rhs;
model.sense = sense;
model.lb = lb;
model.ub = ub;
model.vtype = repmat('C', nvar, 1);
model.modelsense = 'min';
model.obj = zeros(nvar,1);
model.Q = sparse(nvar,nvar);

base = struct();
base.model = model;
base.idx = idx;
base.N = N;
base.T = T;
base.B = B;
base.L = L;
base.nvar = nvar;
base.cacheKey = feeder_qp_cache_key(data);
end

function M = expand_col_to_matrix(v, nrow, T)
v = v(:);
if isscalar(v)
    v = repmat(v, nrow, 1);
end
if numel(v) ~= nrow
    error('expand_col_to_matrix:BadSize', 'Expected scalar or %d-element vector, got %d.', nrow, numel(v));
end
M = repmat(v, 1, T);
end

function key = feeder_qp_cache_key(data)
key = sprintf(['N=%d|T=%d|B=%d|L=%d|root=%d|branch=%s|r=%s|x=%s|Vsl=%.12g|' ...
               'Vmin=%s|Vmax=%s|Pgrid=%s|Qmin=%s|Qmax=%s|Pbus=%s|Qbus=%s|' ...
               'Pij=%s|Qij=%s|Psub=%s|hascomm=%s|map=%s|baseMVA=%.12g'], ...
    data.N, data.T, data.B, data.L, data.rootBus, local_sig(data.branch), ...
    local_sig(data.rline), local_sig(data.xline), data.Vslack, local_sig(data.Vmin), ...
    local_sig(data.Vmax), local_sig(data.PgridMax), local_sig(data.QinjMin), ...
    local_sig(data.QinjMax), local_sig(data.PbusBase), local_sig(data.QbusBase), ...
    local_sig(data.PijMax), local_sig(data.QijMax), local_sig(data.PsubMax), ...
    local_sig(double(data.bus_has_comm)), local_sig(data.bus_to_comm), data.baseMVA);
end

function s = local_sig(x)
sz = size(x);
x = double(x(:));
if isempty(x)
    s = sprintf('sz=%s;n=0', mat2str(sz));
else
    s = sprintf('sz=%s;n=%d;s1=%.16g;s2=%.16g;mn=%.16g;mx=%.16g', ...
        mat2str(sz), numel(x), sum(x), sum(x.^2), min(x), max(x));
end
end
