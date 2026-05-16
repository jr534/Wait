#include <QCoreApplication>
#include "wait_server.h"

int main(int argc, char *argv[])
{
    QCoreApplication a(argc, argv);

    wait_Server server(&a);
    server.start_waitServer(1234);


    return a.exec();
}
