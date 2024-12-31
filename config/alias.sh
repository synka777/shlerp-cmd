shlerp() {
    # Determine the directory of the script itself
    script_dir="$(cd "$(dirname "${(%):-%x}")" && pwd)"
    setup_dir="$(cd "$script_dir/.." && pwd)"  # Move up one level to the project root

    # Construct the command with the virtual environment activation
    cmd="source ${setup_dir}/venv/bin/activate && python3 ${setup_dir}/main.py"

    # Initialize variables for -u
    u_flag=false
    u_value=""

    # Parse arguments
    remaining_args=()
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -u)
                u_flag=true
                if [[ -n "$2" && "$2" != -* ]]; then
                    u_value="$2"
                    shift
                else
                    u_value="default"
                fi
                ;;
            -h)
                remaining_args+=("--help")
                ;;
            *)
                remaining_args+=("$1")
                ;;
        esac
        shift
    done

    # Add -u if specified
    if $u_flag; then
        cmd+=" -u $u_value"
    fi

    # Append remaining arguments
    for arg in "${remaining_args[@]}"; do
        cmd+=" \"$arg\""
    done

    # Execute the constructed command
    eval $cmd
}
