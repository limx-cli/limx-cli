cmake_minimum_required(VERSION 3.16)
project(limx_cli)

find_program(BASH_EXECUTABLE bash REQUIRED)

set(LIMX_CLI_BUNDLE_NAME "limx-cli" CACHE STRING "Name of the generated deployment bundle directory")
set(LIMX_CLI_BUNDLE_DIR "${CMAKE_CURRENT_BINARY_DIR}/${LIMX_CLI_BUNDLE_NAME}")
set(LIMX_CLI_STAMP "${CMAKE_CURRENT_BINARY_DIR}/.${LIMX_CLI_BUNDLE_NAME}.stamp")
set(LIMX_CLI_NODE_VERSION "22.22.0" CACHE STRING "Node.js version bundled into the deployment target")
set(LIMX_CLI_NODE_ARCH "" CACHE STRING "Node.js target architecture for the deployment target: x64 or arm64. Empty auto-detects from CMake target processor.")
set(LIMX_CLI_NODE_EXECUTABLE "node" CACHE FILEPATH "Node.js executable used by local run mode")

option(LIMX_CLI_SKIP_SCRATCH_BUILD "Reuse existing scratch-static/vendor and only rebuild the copyable bundle" OFF)
option(LIMX_CLI_CLEAN_FIRST "Clean generated limx-cli outputs before building" ON)

set(_limx_cli_mode "build")
if(LIMX_CLI_SKIP_SCRATCH_BUILD)
  set(_limx_cli_mode "target")
endif()

set(_limx_cli_clean_arg "")
if(LIMX_CLI_CLEAN_FIRST)
  set(_limx_cli_clean_arg "--clean")
endif()

set_property(DIRECTORY APPEND PROPERTY ADDITIONAL_CLEAN_FILES
  "${LIMX_CLI_BUNDLE_DIR}"
  "${LIMX_CLI_STAMP}"
  "${CMAKE_CURRENT_SOURCE_DIR}/.node-runtime"
  "${CMAKE_CURRENT_SOURCE_DIR}/target"
  "${CMAKE_CURRENT_SOURCE_DIR}/scratch-static"
  "${CMAKE_CURRENT_SOURCE_DIR}/limx-cli/vendor/scratch-app"
  "${CMAKE_CURRENT_SOURCE_DIR}/dist"
  "${CMAKE_CURRENT_SOURCE_DIR}/limx_cli.egg-info"
  "${CMAKE_CURRENT_SOURCE_DIR}/__pycache__"
  "${CMAKE_CURRENT_SOURCE_DIR}/tests/__pycache__"
  "${CMAKE_CURRENT_SOURCE_DIR}/limx-cli/__pycache__"
)

set(_limx_cli_effective_node_arch "${LIMX_CLI_NODE_ARCH}")
if(_limx_cli_effective_node_arch STREQUAL "")
  set(_limx_cli_detect_processor "${CMAKE_SYSTEM_PROCESSOR}")
  if(_limx_cli_detect_processor STREQUAL "")
    set(_limx_cli_detect_processor "${CMAKE_HOST_SYSTEM_PROCESSOR}")
  endif()
  string(TOLOWER "${_limx_cli_detect_processor}" _limx_cli_detect_processor)

  if(_limx_cli_detect_processor MATCHES "^(aarch64|arm64)$")
    set(_limx_cli_effective_node_arch "arm64")
  elseif(_limx_cli_detect_processor MATCHES "^(x86_64|amd64|x64)$")
    set(_limx_cli_effective_node_arch "x64")
  else()
    message(FATAL_ERROR "Unsupported processor for bundled Node.js runtime: ${_limx_cli_detect_processor}. Set LIMX_CLI_NODE_ARCH to x64 or arm64.")
  endif()
endif()
message(STATUS "LimX CLI bundled Node.js architecture: ${_limx_cli_effective_node_arch}")

add_custom_command(
  OUTPUT "${LIMX_CLI_STAMP}"
  COMMAND
    "${CMAKE_COMMAND}" -E env
      "LIMX_SCRATCH_TARGET_DIR=${LIMX_CLI_BUNDLE_DIR}"
      "${BASH_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/scripts/build-limx-cli.sh"
        "${_limx_cli_mode}"
        ${_limx_cli_clean_arg}
        "--target-dir" "${LIMX_CLI_BUNDLE_DIR}"
        "--node-version" "${LIMX_CLI_NODE_VERSION}"
        "--node" "${LIMX_CLI_NODE_EXECUTABLE}"
        "--node-arch" "${_limx_cli_effective_node_arch}"
  COMMAND "${CMAKE_COMMAND}" -E touch "${LIMX_CLI_STAMP}"
  WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
  COMMENT "Building ${LIMX_CLI_BUNDLE_NAME} deployment bundle"
  VERBATIM
)

add_custom_target(${PROJECT_NAME}_bundle ALL DEPENDS "${LIMX_CLI_STAMP}")

install(
  DIRECTORY
    "${LIMX_CLI_BUNDLE_DIR}/python"
    "${LIMX_CLI_BUNDLE_DIR}/scratch-static"
    "${LIMX_CLI_BUNDLE_DIR}/node"
  DESTINATION bin/limx-cli.bin
  USE_SOURCE_PERMISSIONS
)

install(
  FILES "${LIMX_CLI_BUNDLE_DIR}/README.txt"
  DESTINATION bin/limx-cli.bin
)

install(
  PROGRAMS
    "${LIMX_CLI_BUNDLE_DIR}/limx-cli"
    "${LIMX_CLI_BUNDLE_DIR}/limx-scratch"
  DESTINATION bin
)
