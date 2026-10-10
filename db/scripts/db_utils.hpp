#pragma once

// Database connection and repositories for the Neon schema.
// The live driver is optional: this header does not link libpq.
// NeonDBConnection throws if a real connection is requested without EMEC_HAS_LIBPQ.
// Callers that only need the SQL surface can pass any DbConnection (including a test double).

#include <fstream>
#include <map>
#include <memory>
#include <optional>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace emec {

using QueryRow = std::map<std::string, std::string>;

class DbConnection {
public:
    virtual ~DbConnection() = default;
    virtual std::vector<QueryRow> execute_query(const std::string& query, const std::vector<std::string>& params = {}) = 0;
    virtual int execute_command(const std::string& command, const std::vector<std::string>& params = {}) = 0;
    virtual int executemany(const std::string& query, const std::vector<std::vector<std::string>>& rows) = 0;
    virtual void execute_script(const std::string& script_path) = 0;
};

class NeonDBConnection : public DbConnection {
public:
    explicit NeonDBConnection(std::string connection_string) : connection_string_(std::move(connection_string)) {
        if (connection_string_.empty()) {
            throw std::invalid_argument(
                "Database connection string not provided. Set NEON_DATABASE_URL or pass connection_string.");
        }
#ifndef EMEC_HAS_LIBPQ
        throw std::runtime_error(
            "libpq is not linked. Device persistence stays disabled unless a DbConnection is injected.");
#else
        (void)connection_string_;
#endif
    }

    std::vector<QueryRow> execute_query(const std::string&, const std::vector<std::string>& = {}) override {
        throw std::runtime_error("NeonDBConnection has no live driver in this build");
    }
    int execute_command(const std::string&, const std::vector<std::string>& = {}) override {
        throw std::runtime_error("NeonDBConnection has no live driver in this build");
    }
    int executemany(const std::string&, const std::vector<std::vector<std::string>>&) override {
        throw std::runtime_error("NeonDBConnection has no live driver in this build");
    }
    void execute_script(const std::string& script_path) override {
        std::ifstream file(script_path);
        if (!file) {
            throw std::runtime_error("failed to open SQL script: " + script_path);
        }
        throw std::runtime_error("NeonDBConnection has no live driver in this build");
    }

    const std::string& connection_string() const { return connection_string_; }

private:
    std::string connection_string_;
};

class ModelRepository {
public:
    explicit ModelRepository(std::shared_ptr<DbConnection> db) : db_(std::move(db)) {}

    std::string create_model(const std::string& model_name,
                             const std::string& model_type,
                             const std::string& architecture_config_json,
                             const std::string& version) {
        const char* query =
            "INSERT INTO models (model_name, model_type, architecture_config, version) "
            "VALUES ($1, $2, $3::jsonb, $4) RETURNING model_id::text";
        auto rows = db_->execute_query(query, {model_name, model_type, architecture_config_json, version});
        return rows.at(0).at("model_id");
    }

    std::optional<QueryRow> get_model(const std::string& model_id) {
        auto rows = db_->execute_query("SELECT * FROM models WHERE model_id = $1::uuid", {model_id});
        if (rows.empty()) {
            return std::nullopt;
        }
        return rows[0];
    }

    std::vector<QueryRow> list_models(std::optional<std::string> status = std::nullopt) {
        if (status) {
            return db_->execute_query("SELECT * FROM models WHERE status = $1 ORDER BY created_at DESC", {*status});
        }
        return db_->execute_query("SELECT * FROM models ORDER BY created_at DESC");
    }

private:
    std::shared_ptr<DbConnection> db_;
};

class TensorRepository {
public:
    explicit TensorRepository(std::shared_ptr<DbConnection> db) : db_(std::move(db)) {}

    std::string create_tensor(const std::string& tensor_name,
                              const std::string& tensor_type,
                              const std::string& model_id,
                              const std::vector<int>& shape,
                              const std::string& dtype = "float32") {
        long long total = 1;
        std::ostringstream shape_text;
        shape_text << '{';
        for (std::size_t i = 0; i < shape.size(); ++i) {
            if (i) {
                shape_text << ',';
            }
            shape_text << shape[i];
            total *= shape[i];
        }
        shape_text << '}';
        const char* query =
            "INSERT INTO tensor_metadata (tensor_name, tensor_type, model_id, shape, dtype, total_elements) "
            "VALUES ($1, $2, $3::uuid, $4::integer[], $5, $6) RETURNING tensor_id::text";
        auto rows = db_->execute_query(query, {tensor_name, tensor_type, model_id, shape_text.str(), dtype, std::to_string(total)});
        return rows.at(0).at("tensor_id");
    }

    void store_tensor_data(const std::string& tensor_id, const std::string& data, int chunk_index = 0) {
        db_->execute_command(
            "INSERT INTO tensor_data (tensor_id, chunk_index, data) VALUES ($1::uuid, $2, $3)",
            {tensor_id, std::to_string(chunk_index), data});
    }

private:
    std::shared_ptr<DbConnection> db_;
};

class ReactorRepository {
public:
    explicit ReactorRepository(std::shared_ptr<DbConnection> db) : db_(std::move(db)) {}

    std::string create_reactor(const std::string& reactor_name, const std::string& reactor_type, const std::string& config_json) {
        auto rows = db_->execute_query(
            "INSERT INTO reactors (reactor_name, reactor_type, config) VALUES ($1, $2, $3::jsonb) RETURNING reactor_id::text",
            {reactor_name, reactor_type, config_json});
        return rows.at(0).at("reactor_id");
    }

    void add_model_to_reactor(const std::string& reactor_id, const std::string& model_id, const std::string& role) {
        db_->execute_command(
            "INSERT INTO reactor_models (reactor_id, model_id, role) VALUES ($1::uuid, $2::uuid, $3)",
            {reactor_id, model_id, role});
    }

    std::optional<QueryRow> get_reactor_status(const std::string& reactor_id) {
        auto rows = db_->execute_query("SELECT * FROM reactors WHERE reactor_id = $1::uuid", {reactor_id});
        if (rows.empty()) {
            return std::nullopt;
        }
        return rows[0];
    }

private:
    std::shared_ptr<DbConnection> db_;
};

}  // namespace emec
