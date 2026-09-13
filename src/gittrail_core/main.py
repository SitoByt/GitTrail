from gittrail_core.track.pipeline import init_local, init_remote


def main():
    path = ""
    while not path:
        print("What kind of repository do you want to analyze?\n\t[1] local\n\t[2] remote")
        choice = input()
        if choice == 1:
            path = init_local()
        elif choice == 2:
            path = init_remote()

    # TODO: as soon as we implement an update-function:
    #print("What do you want to do?\n\t[1] new track\n\t[2] update track")


    

    

if __name__ == "__main__":
    main()