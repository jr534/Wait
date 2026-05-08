cmake_minimum_required(VERSION 3.20)

project(wait-backend LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(Qt6 REQUIRED COMPONENTS Core WebSockets)

qt_standard_project_setup()

qt_add_executable(wait-backend
    src/main.cpp
)

target_link_libraries(wait-backend
    PRIVATE
        Qt6::Core
        Qt6::WebSockets
)
