cmake_minimum_required(VERSION 3.16)
project(agent_harness)

find_program(BASH_EXECUTABLE bash REQUIRED)

set(AGENT_HARNESS_BUNDLE_NAME "agent-harness" CACHE STRING "Name of the generated deployment bundle directory")
set(AGENT_HARNESS_BUNDLE_DIR "${CMAKE_CURRENT_BINARY_DIR}/${AGENT_HARNESS_BUNDLE_NAME}")
set(AGENT_HARNESS_STAMP "${CMAKE_CURRENT_BINARY_DIR}/.${AGENT_HARNESS_BUNDLE_NAME}.stamp")
set(AGENT_HARNESS_NODE_VERSION "22.22.0" CACHE STRING "Node.js version bundled into the deployment target")
set(AGENT_HARNESS_NODE_ARCH "" CACHE STRING "Node.js target architecture for the deployment target: x64 or arm64. Empty auto-detects from CMake target processor.")
set(AGENT_HARNESS_NODE_EXECUTABLE "node" CACHE FILEPATH "Node.js executable used by local run mode")

option(AGENT_HARNESS_SKIP_SCRATCH_BUILD "Reuse existing scratch-static/vendor and only rebuild the copyable bundle" OFF)
option(AGENT_HARNESS_CLEAN_FIRST "Clean generated agent-harness outputs before building" ON)

set(_agent_harness_mode "build")
if(AGENT_HARNESS_SKIP_SCRATCH_BUILD)
  set(_agent_harness_mode "target")
endif()

set(_agent_harness_clean_arg "")
if(AGENT_HARNESS_CLEAN_FIRST)
  set(_agent_harness_clean_arg "--clean")
endif()

set_property(DIRECTORY APPEND PROPERTY ADDITIONAL_CLEAN_FILES
  "${AGENT_HARNESS_BUNDLE_DIR}"
  "${AGENT_HARNESS_STAMP}"
  "${CMAKE_CURRENT_SOURCE_DIR}/.node-runtime"
  "${CMAKE_CURRENT_SOURCE_DIR}/target"
  "${CMAKE_CURRENT_SOURCE_DIR}/scratch-static"
  "${CMAKE_CURRENT_SOURCE_DIR}/agent_harness/vendor/scratch-app"
  "${CMAKE_CURRENT_SOURCE_DIR}/dist"
  "${CMAKE_CURRENT_SOURCE_DIR}/limx_agent_harness.egg-info"
  "${CMAKE_CURRENT_SOURCE_DIR}/__pycache__"
  "${CMAKE_CURRENT_SOURCE_DIR}/tests/__pycache__"
  "${CMAKE_CURRENT_SOURCE_DIR}/agent_harness/__pycache__"
)

set(_agent_harness_effective_node_arch "${AGENT_HARNESS_NODE_ARCH}")
if(_agent_harness_effective_node_arch STREQUAL "")
  set(_agent_harness_detect_processor "${CMAKE_SYSTEM_PROCESSOR}")
  if(_agent_harness_detect_processor STREQUAL "")
    set(_agent_harness_detect_processor "${CMAKE_HOST_SYSTEM_PROCESSOR}")
  endif()
  string(TOLOWER "${_agent_harness_detect_processor}" _agent_harness_detect_processor)

  if(_agent_harness_detect_processor MATCHES "^(aarch64|arm64)$")
    set(_agent_harness_effective_node_arch "arm64")
  elseif(_agent_harness_detect_processor MATCHES "^(x86_64|amd64|x64)$")
    set(_agent_harness_effective_node_arch "x64")
  else()
    message(FATAL_ERROR "Unsupported processor for bundled Node.js runtime: ${_agent_harness_detect_processor}. Set AGENT_HARNESS_NODE_ARCH to x64 or arm64.")
  endif()
endif()
message(STATUS "Agent harness bundled Node.js architecture: ${_agent_harness_effective_node_arch}")

add_custom_command(
  OUTPUT "${AGENT_HARNESS_STAMP}"
  COMMAND
    "${CMAKE_COMMAND}" -E env
      "LIMX_SCRATCH_TARGET_DIR=${AGENT_HARNESS_BUNDLE_DIR}"
      "${BASH_EXECUTABLE}" "${CMAKE_CURRENT_SOURCE_DIR}/scripts/build-agent-harness.sh"
        "${_agent_harness_mode}"
        ${_agent_harness_clean_arg}
        "--target-dir" "${AGENT_HARNESS_BUNDLE_DIR}"
        "--node-version" "${AGENT_HARNESS_NODE_VERSION}"
        "--node" "${AGENT_HARNESS_NODE_EXECUTABLE}"
        "--node-arch" "${_agent_harness_effective_node_arch}"
  COMMAND "${CMAKE_COMMAND}" -E touch "${AGENT_HARNESS_STAMP}"
  WORKING_DIRECTORY "${CMAKE_CURRENT_SOURCE_DIR}"
  COMMENT "Building ${AGENT_HARNESS_BUNDLE_NAME} deployment bundle"
  VERBATIM
)

add_custom_target(${PROJECT_NAME}_bundle ALL DEPENDS "${AGENT_HARNESS_STAMP}")

install(
  DIRECTORY "${AGENT_HARNESS_BUNDLE_DIR}"
  DESTINATION bin
  USE_SOURCE_PERMISSIONS
  PATTERN "limx-cli" EXCLUDE
  PATTERN "limx-scratch" EXCLUDE
)

install(
  PROGRAMS
    "${AGENT_HARNESS_BUNDLE_DIR}/limx-cli"
    "${AGENT_HARNESS_BUNDLE_DIR}/limx-scratch"
  DESTINATION bin
)
