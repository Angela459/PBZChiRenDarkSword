cmake_minimum_required(VERSION 3.22)
project(PBZChiRenNativeAudio LANGUAGES CXX)

add_library(PBZChiRenNativeAudio SHARED dllmain.cpp)
target_compile_features(PBZChiRenNativeAudio PRIVATE cxx_std_20)
target_compile_definitions(PBZChiRenNativeAudio PRIVATE UNICODE _UNICODE)
target_compile_options(PBZChiRenNativeAudio PRIVATE /W4 /EHsc /MD)
target_link_libraries(PBZChiRenNativeAudio PRIVATE "${UE4SS_IMPORT_LIBRARY}" winmm)
set_target_properties(PBZChiRenNativeAudio PROPERTIES PREFIX "" OUTPUT_NAME "main")
